from types import SimpleNamespace

import pytest

from app.datavideo import cli
from app.datavideo.channels import CHANNELS_DIRECTORY, load_channel
from app.datavideo.pipeline import BlockedPublication
from app.datavideo.script import ScriptRejected

PROFILE = load_channel(CHANNELS_DIRECTORY / "tu_dinero_es.toml")
PRODUCTION = SimpleNamespace(
    run=SimpleNamespace(story_key="ipc_anual_ccaa_2026_09", directory="/runs/ipc"),
    video_path="/runs/ipc/final.mp4",
    package=SimpleNamespace(title="Galicia lidera"),
    quality=SimpleNamespace(passed=True, problems=()),
)


class Alerts(list):
    def __call__(self, text):
        self.append(text)
        return True


def run(publish_videos=True, produce=lambda profile, story: PRODUCTION, publish=None, alerts=None):
    return cli.run_channel(
        PROFILE,
        publish_videos,
        produce_story=produce,
        publish_production=publish or (lambda production, profile: {"success": True, "request_id": "abc"}),
        alert=alerts if alerts is not None else Alerts(),
    )


def test_a_published_story_is_reported_without_alerting_the_owner():
    alerts = Alerts()

    outcome = run(alerts=alerts)

    assert outcome.failed is False
    assert any("ipc_anual_ccaa_2026_09" in line and "abc" in line for line in outcome.lines)
    assert alerts == []


def test_producing_only_never_publishes():
    outcome = run(publish_videos=False, publish=lambda production, profile: pytest.fail("published"))

    assert any("final.mp4" in line for line in outcome.lines)


def test_nothing_new_is_a_quiet_success():
    alerts = Alerts()

    outcome = run(produce=lambda profile, story: None, alerts=alerts)

    assert outcome.failed is False
    assert alerts == []


def test_a_blocked_publication_alerts_the_owner_with_the_reason():
    alerts = Alerts()

    def blocked(production, profile):
        raise BlockedPublication("technical checks failed: loudness")

    outcome = run(publish=blocked, alerts=alerts)

    assert outcome.failed is True
    assert "loudness" in alerts[0] and "tu_dinero_es" in alerts[0]


def test_a_rejected_script_alerts_the_owner_with_its_problems():
    alerts = Alerts()

    def rejected(profile, story):
        raise ScriptRejected(["the title used figures that are not in the facts: 40"])

    outcome = run(produce=rejected, alerts=alerts)

    assert outcome.failed is True
    assert "40" in alerts[0]


def test_an_unexpected_error_alerts_the_owner_and_fails_the_run():
    alerts = Alerts()

    def broken(profile, story):
        raise ConnectionError("INE unreachable")

    outcome = run(produce=broken, alerts=alerts)

    assert outcome.failed is True
    assert "INE unreachable" in alerts[0]


def test_a_profile_listing_an_unknown_story_is_rejected():
    profile = load_channel(CHANNELS_DIRECTORY / "tu_dinero_es.toml")
    broken = profile.__class__(**{**profile.__dict__, "stories": ("no_existe",)})

    with pytest.raises(ValueError, match="no_existe"):
        cli.run_channel(broken, True, alert=Alerts())


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
