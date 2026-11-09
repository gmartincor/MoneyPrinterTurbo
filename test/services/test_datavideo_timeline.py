from types import SimpleNamespace

import pytest

from app.datavideo import timeline
from app.datavideo.timeline import narrate, segment_durations

TICKS_PER_SECOND = 10_000_000


def words(*entries):
    texts = [text for text, _, _ in entries]
    offsets = [(round(start * TICKS_PER_SECOND), round(end * TICKS_PER_SECOND)) for _, start, end in entries]
    return texts, offsets


def test_each_segment_lasts_until_halfway_through_the_pause_before_the_next():
    texts, offsets = words(
        ("La", 0.1, 0.3), ("inflación", 0.3, 0.9), ("sube.", 0.9, 1.4),
        ("Galicia", 1.8, 2.4), ("lidera.", 2.4, 3.0),
    )

    durations = segment_durations(["La inflación sube.", "Galicia lidera."], texts, offsets, total_seconds=3.5)

    assert durations == pytest.approx([1.6, 1.9])


def test_durations_add_up_to_the_whole_audio():
    texts, offsets = words(("Uno", 0.0, 0.5), ("dos", 1.0, 1.5), ("tres", 2.0, 2.5))

    durations = segment_durations(["Uno", "dos", "tres"], texts, offsets, total_seconds=3.0)

    assert sum(durations) == pytest.approx(3.0)


def test_figures_punctuation_and_accents_are_matched_by_letters_and_digits_only():
    texts, offsets = words(
        ("Castilla", 0.0, 0.4), ("-", 0.4, 0.45), ("La", 0.45, 0.6), ("Mancha", 0.6, 1.0),
        ("5,5", 1.0, 1.6), ("%", 1.6, 1.9), ("Ceuta", 2.4, 2.9), ("3,1", 2.9, 3.4), ("%.", 3.4, 3.7),
    )

    durations = segment_durations(
        ["Castilla-La Mancha, 5,5 %.", "Ceuta, 3,1 %."], texts, offsets, total_seconds=4.0
    )

    assert durations == pytest.approx([2.15, 1.85])


def test_a_word_the_voice_skipped_does_not_break_the_alignment():
    texts, offsets = words(("Hola", 0.0, 0.5), ("mundo", 1.0, 1.5))

    durations = segment_durations(["Hola, querido", "mundo"], texts, offsets, total_seconds=2.0)

    assert durations == pytest.approx([0.75, 1.25])


def test_a_segment_without_any_spoken_word_is_rejected():
    texts, offsets = words(("Hola", 0.0, 0.5))

    with pytest.raises(ValueError, match="segment 2"):
        segment_durations(["Hola", "Adiós"], texts, offsets, total_seconds=1.0)


def test_narration_uses_the_profile_voice_and_writes_audio_and_subtitles(tmp_path, monkeypatch):
    calls = {}
    texts, offsets = words(("Hola", 0.0, 0.5), ("mundo", 1.0, 1.5))

    def fake_tts(text, voice_name, voice_rate, voice_file):
        calls["tts"] = (text, voice_name, voice_rate, voice_file)
        return SimpleNamespace(subs=texts, offset=offsets)

    def fake_subtitle(sub_maker, text, subtitle_file):
        calls["subtitle"] = (text, subtitle_file)

    monkeypatch.setattr(timeline.voice, "tts", fake_tts)
    monkeypatch.setattr(timeline.voice, "create_subtitle", fake_subtitle)
    monkeypatch.setattr(timeline.voice, "get_audio_duration", lambda path: 2.0)

    result = narrate(["Hola", "mundo"], "es-ES-TristanMultilingualNeural-V2-Male", 1.0, tmp_path)

    assert calls["tts"][0] == "Hola mundo"
    assert calls["tts"][1] == "es-ES-TristanMultilingualNeural-V2-Male"
    assert calls["subtitle"][0] == "Hola mundo"
    assert result.durations == pytest.approx((0.75, 1.25))
    assert result.audio_path == tmp_path / "narration.mp3"
    assert result.subtitle_path == tmp_path / "narration.srt"


def test_narration_fails_loudly_when_the_voice_returns_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(timeline.voice, "tts", lambda **arguments: None)

    with pytest.raises(RuntimeError, match="voice"):
        narrate(["Hola"], "es-ES-TristanMultilingualNeural-V2-Male", 1.0, tmp_path)


def test_azure_key_from_the_environment_is_used_without_saving_it(monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "fixture-key")
    monkeypatch.setitem(timeline.config.azure, "speech_key", "")

    timeline.use_azure_key_from_environment()

    assert timeline.config.azure["speech_key"] == "fixture-key"
