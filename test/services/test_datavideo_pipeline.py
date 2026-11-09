import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from app.datavideo import pipeline
from app.datavideo.channels import CHANNELS_DIRECTORY, load_channel
from app.datavideo.pipeline import BlockedPublication, produce, publish
from app.datavideo.qa import QualityReport
from app.datavideo.facts import Source
from app.datavideo.store import PUBLICATION_FILE
from app.datavideo.stories.regional_ranking import CPI_ANNUAL_BY_REGION
from app.datavideo.timeline import Narration
from app.services.video import get_ffmpeg_binary

FIXTURE = Path(__file__).parent / "fixtures" / "datavideo" / "ine_table_76140.json"
SMALL_VERTICAL = (180, 320)
NARRATION_SECONDS = 16
SEGMENTS = [
    ("En septiembre de 2026, Castilla-La Mancha y Galicia tuvieron la inflación anual más alta de España, un 5,5 %.",
     ["highest", "period"], "big_number"),
    ("La media nacional se quedó en el 4,9 %, y 10 de 19 comunidades y ciudades autónomas la superaron.",
     ["national", "above_national"], "ranking"),
    ("En el otro extremo está Ceuta, con la inflación más baja del país: un 3,1 %.", ["lowest"], "big_number"),
    ("Entre la más alta y la más baja hay 2,4 puntos de diferencia.", ["gap"], "big_number"),
    ("Son datos oficiales del INE.", [], "source_card"),
]
SCRIPT_REPLY = json.dumps(
    {
        "title": "Dónde subieron más los precios en septiembre",
        "segments": [{"text": text, "facts": facts, "scene": scene} for text, facts, scene in SEGMENTS],
    },
    ensure_ascii=False,
)


def profile():
    return load_channel(CHANNELS_DIRECTORY / "tu_dinero_es.toml")


def fake_download(table_id, periods):
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class CountingWriter:
    def __init__(self):
        self.calls = 0

    def __call__(self, prompt):
        self.calls += 1
        return SCRIPT_REPLY


def fake_narrate(segment_texts, voice_name, rate, directory):
    audio = directory / "narration.mp3"
    subprocess.run(
        [
            get_ffmpeg_binary(), "-v", "error", "-y", "-f", "lavfi",
            "-i", f"sine=frequency=300:duration={NARRATION_SECONDS}", "-af", "volume=0.5", str(audio),
        ],
        check=True,
    )
    subtitle = directory / "narration.srt"
    subtitle.write_text("1\n00:00:00,000 --> 00:00:02,000\nEn septiembre\n", encoding="utf-8")
    share = NARRATION_SECONDS / len(segment_texts)
    return Narration(audio_path=audio, subtitle_path=subtitle, durations=tuple(share for _ in segment_texts))


@pytest.fixture(scope="module")
def rendered_runs(tmp_path_factory):
    root = tmp_path_factory.mktemp("runs")
    writer = CountingWriter()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pipeline, "narrate", fake_narrate)
        produce(profile(), CPI_ANNUAL_BY_REGION, root=root, download=fake_download, generate=writer, size=SMALL_VERTICAL)
    assert writer.calls == 1
    return root


@pytest.fixture
def produced(rendered_runs, tmp_path, monkeypatch):
    root = tmp_path / "runs"
    shutil.copytree(rendered_runs, root)
    monkeypatch.setattr(pipeline, "narrate", lambda *arguments: pytest.fail("narrated again"))
    writer = CountingWriter()
    production = produce(
        profile(), CPI_ANNUAL_BY_REGION, root=root, download=fake_download, generate=writer, size=SMALL_VERTICAL
    )
    return production, writer, root


def test_a_production_leaves_every_artefact_in_its_run_folder(produced):
    production, _, _ = produced

    for name in ("source.json", "facts.json", "script.json", "timeline.json", "voice.mp3", "scenes.mp4",
                 "final.mp4", "quality.json", "package.json"):
        assert production.run.has(name), name
    assert production.run.story_key == "ipc_anual_ccaa_2026_09"


def test_the_finished_video_passes_the_technical_checks(produced):
    production, _, _ = produced

    assert production.quality.passed, production.quality.problems


def test_the_package_credits_the_ine_and_uses_the_script_title(produced):
    production, _, _ = produced

    assert production.package.title == "Dónde subieron más los precios en septiembre"
    assert "INE" in production.package.description


def test_the_source_response_is_kept_with_its_licence_for_audit(produced):
    production, _, _ = produced

    source = production.run.read_json("source.json")
    assert source["table_id"] == 76140
    assert source["license_verified"] is True
    assert source["payload"] == fake_download(76140, 3)


def test_an_interrupted_run_resumes_without_writing_the_script_again(produced, monkeypatch):
    production, writer, root = produced

    produce(profile(), CPI_ANNUAL_BY_REGION, root=root, download=fake_download, generate=writer, size=SMALL_VERTICAL)

    assert writer.calls == 0


def test_a_story_already_published_is_not_produced_again(produced):
    production, writer, root = produced
    production.run.write_json(PUBLICATION_FILE, {"success": True})

    again = produce(profile(), CPI_ANNUAL_BY_REGION, root=root, download=fake_download, generate=writer, size=SMALL_VERTICAL)

    assert again is None


def test_publishing_records_the_upload_and_never_repeats_it(produced, monkeypatch):
    production, _, _ = produced
    monkeypatch.setenv("UPLOAD_POST_API_KEY", "fixture-key")
    uploads = []

    def fake_cross_post(**kwargs):
        uploads.append(kwargs)
        return {"success": True, "request_id": "abc"}

    first = publish(production, profile(), cross_post=fake_cross_post)
    second = publish(production, profile(), cross_post=fake_cross_post)

    assert len(uploads) == 1
    assert first == second
    assert first["success"] is True
    assert first["request_id"] == "abc"
    assert first["privacy"] == "private"


def test_a_video_that_failed_the_checks_is_not_published(produced):
    production, _, _ = produced
    failed = replace(production, quality=QualityReport(problems=("video has no audio track",), duration=1.0, loudness=None))

    with pytest.raises(BlockedPublication, match="audio"):
        publish(failed, profile(), cross_post=lambda **kwargs: pytest.fail("uploaded"))


def test_facts_from_a_source_without_a_verified_licence_are_not_published(produced):
    production, _, _ = produced
    unverified = Source(name="Fuente sin revisar", url="https://example.org", license="?")
    facts = tuple(replace(fact, source=unverified) for fact in production.facts)

    with pytest.raises(BlockedPublication, match="licence"):
        publish(replace(production, facts=facts), profile(), cross_post=lambda **kwargs: pytest.fail("uploaded"))


def test_an_unconfirmed_earlier_upload_is_never_retried_automatically(produced, monkeypatch):
    production, _, _ = produced
    monkeypatch.setenv("UPLOAD_POST_API_KEY", "fixture-key")
    production.run.write_json(PUBLICATION_FILE, {"success": False, "request_id": "abc", "error": "timeout"})

    with pytest.raises(BlockedPublication, match="abc"):
        publish(production, profile(), cross_post=lambda **kwargs: pytest.fail("uploaded"))


def test_a_failed_upload_is_recorded_and_reported(produced, monkeypatch):
    production, _, _ = produced
    monkeypatch.setenv("UPLOAD_POST_API_KEY", "fixture-key")

    with pytest.raises(RuntimeError, match="quota"):
        publish(production, profile(), cross_post=lambda **kwargs: {"success": False, "error": "quota exceeded"})

    assert production.run.read_json(PUBLICATION_FILE)["success"] is False
