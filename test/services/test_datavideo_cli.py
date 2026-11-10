from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.datavideo import cli
from app.datavideo.channels import CHANNELS_DIRECTORY, load_channel
from app.datavideo.pipeline import BlockedPublication
from app.datavideo.script import ScriptRejected
from app.datavideo.stories.regional_ranking import STORIES

BASE_PROFILE = load_channel(CHANNELS_DIRECTORY / "tu_dinero_es.toml")
PROFILE = replace(BASE_PROFILE, stories=("ipc_anual_ccaa", "paro_ccaa", "salario_ccaa"))
NOW = datetime(2026, 11, 10, 11, 0, tzinfo=timezone.utc)


def production(key, score=40):
    story = STORIES[key]
    story_key = f"{key}_2026_t3"
    return SimpleNamespace(
        run=SimpleNamespace(story_key=story_key, directory=f"/runs/{story_key}"),
        story=story,
        video_path=f"/runs/{story_key}/final.mp4",
        package=SimpleNamespace(title=f"Título de {key}"),
        quality=SimpleNamespace(passed=True, problems=()),
        review=SimpleNamespace(total=score),
    )


class Alerts(list):
    def __call__(self, text):
        self.append(text)
        return True


class Uploads(list):
    def __call__(self, production, profile):
        self.append(production.story.key)
        return {"success": True, "request_id": f"id-{production.story.key}"}


def record(story, published_at):
    return {"success": True, "story": story, "published_at": published_at}


def run(
    profile=PROFILE,
    publish_videos=True,
    produce=lambda profile, story: production(story.key),
    publish=None,
    alerts=None,
    published=None,
):
    return cli.run_channel(
        profile,
        publish_videos,
        now=NOW,
        produce_story=produce,
        publish_production=publish if publish is not None else Uploads(),
        alert=alerts if alerts is not None else Alerts(),
        published=lambda channel: published or {},
    )


def test_only_one_video_a_day_is_published_and_the_rest_wait():
    uploads = Uploads()

    outcome = run(publish=uploads)

    assert uploads == ["ipc_anual_ccaa"]
    assert outcome.failed is False
    assert sum("queued" in line for line in outcome.lines) == 2


def test_nothing_is_published_when_the_channel_already_published_today():
    uploads = Uploads()
    today = {"paro_ccaa_2026_t2": record("paro_ccaa", "2026-11-10T08:30:00+00:00")}

    run(publish=uploads, published=today)

    assert uploads == []


def test_the_day_is_counted_in_the_channel_timezone():
    uploads = Uploads()
    just_after_midnight_in_madrid = {"paro_ccaa_2026_t2": record("paro_ccaa", "2026-11-09T23:30:00+00:00")}

    run(publish=uploads, published=just_after_midnight_in_madrid)

    assert uploads == []


def test_the_table_published_longest_ago_goes_first():
    uploads = Uploads()
    history = {
        "ipc_anual_ccaa_2026_08": record("ipc_anual_ccaa", "2026-11-09T11:00:00+00:00"),
        "paro_ccaa_2026_t2": record("paro_ccaa", "2026-08-01T11:00:00+00:00"),
    }

    run(publish=uploads, published=history)

    assert uploads == ["salario_ccaa"]


def test_a_blocked_video_does_not_use_the_daily_slot():
    uploads = Uploads()
    alerts = Alerts()

    def publish(production, profile):
        if production.story.key == "ipc_anual_ccaa":
            raise BlockedPublication("technical checks failed: loudness")
        return uploads(production, profile)

    outcome = run(publish=publish, alerts=alerts)

    assert uploads == ["paro_ccaa"]
    assert outcome.failed is True
    assert "loudness" in alerts[0] and "tu_dinero_es" in alerts[0]


def test_a_published_story_is_reported_without_alerting_the_owner():
    alerts = Alerts()

    outcome = run(alerts=alerts)

    assert any("ipc_anual_ccaa_2026_t3" in line and "id-ipc_anual_ccaa" in line for line in outcome.lines)
    assert alerts == []


def test_producing_only_never_publishes():
    outcome = run(publish_videos=False, publish=lambda production, profile: pytest.fail("published"))

    assert any("final.mp4" in line for line in outcome.lines)


def test_a_channel_without_publish_settings_alerts_instead_of_publishing():
    alerts = Alerts()

    outcome = run(profile=replace(PROFILE, publish=None), alerts=alerts)

    assert outcome.failed is True
    assert "tu_dinero_es" in alerts[0]


def test_nothing_new_is_a_quiet_success():
    alerts = Alerts()

    outcome = run(produce=lambda profile, story: None, alerts=alerts)

    assert outcome.failed is False
    assert alerts == []


def test_a_rejected_script_alerts_the_owner_and_the_other_stories_still_run():
    alerts = Alerts()
    uploads = Uploads()

    def produce(profile, story):
        if story.key == "ipc_anual_ccaa":
            raise ScriptRejected(["the title used figures that are not in the facts: 40"])
        return production(story.key)

    outcome = run(produce=produce, publish=uploads, alerts=alerts)

    assert outcome.failed is True
    assert "40" in alerts[0]
    assert uploads == ["paro_ccaa"]


def test_an_unexpected_error_alerts_the_owner_and_fails_the_run():
    alerts = Alerts()

    def broken(profile, story):
        raise ConnectionError("INE unreachable")

    outcome = run(produce=broken, alerts=alerts)

    assert outcome.failed is True
    assert "INE unreachable" in alerts[0]


def test_a_profile_listing_an_unknown_story_is_rejected():
    broken = replace(PROFILE, stories=("no_existe",))

    with pytest.raises(ValueError, match="no_existe"):
        cli.run_channel(broken, True, alert=Alerts())


def test_every_story_of_the_real_profiles_exists():
    for profile in cli.load_channels().values():
        assert set(profile.stories) <= set(STORIES), profile.id


def test_the_command_line_returns_a_failure_code_when_the_run_failed(monkeypatch):
    monkeypatch.setattr(cli, "run_channel", lambda profile, publish_videos: cli.Outcome(lines=["x"], failed=True))

    assert cli.main(["run", "tu_dinero_es"]) == 1


def test_the_command_line_rejects_unknown_channels():
    with pytest.raises(SystemExit):
        cli.main(["run", "no_existe"])


def test_the_report_command_sends_the_weekly_digest(monkeypatch):
    sent = Alerts()
    monkeypatch.setattr(cli, "weekly_digest", lambda channel, now: f"Resumen semanal de {channel}")
    monkeypatch.setattr(cli, "send_alert", sent)

    assert cli.main(["report", "tu_dinero_es"]) == 0
    assert sent == ["Resumen semanal de tu_dinero_es"]


def test_among_tables_never_published_the_most_interesting_story_goes_first():
    uploads = Uploads()
    scores = {"ipc_anual_ccaa": 35, "paro_ccaa": 38, "salario_ccaa": 44}

    run(produce=lambda profile, story: production(story.key, scores[story.key]), publish=uploads)

    assert uploads == ["salario_ccaa"]
