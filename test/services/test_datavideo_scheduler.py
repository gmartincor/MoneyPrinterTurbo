import subprocess
from dataclasses import replace
from datetime import datetime, timezone

from app.datavideo import scheduler
from app.datavideo.channels import CHANNELS_DIRECTORY, load_channel

PROFILE = load_channel(CHANNELS_DIRECTORY / "tu_dinero_es.toml")
TUESDAY_BEFORE_NOON_IN_MADRID = datetime(2026, 11, 10, 10, 30, tzinfo=timezone.utc)
TUESDAY_AFTER_NOON_IN_MADRID = datetime(2026, 11, 10, 11, 5, tzinfo=timezone.utc)
WEDNESDAY_AFTER_NOON_IN_MADRID = datetime(2026, 11, 11, 11, 5, tzinfo=timezone.utc)
MONDAY_AFTER_NOON_IN_MADRID = datetime(2026, 11, 16, 11, 5, tzinfo=timezone.utc)


class Executed(list):
    def __call__(self, job):
        self.append((job.command, job.channel))


def tick(root, now, profiles=(PROFILE,)):
    executed = Executed()
    scheduler.tick(profiles, root, now, executed)
    return executed


def test_nothing_runs_before_the_channel_publishing_time(tmp_path):
    assert tick(tmp_path, TUESDAY_BEFORE_NOON_IN_MADRID) == []


def test_the_channel_runs_once_after_its_publishing_time(tmp_path):
    assert tick(tmp_path, TUESDAY_AFTER_NOON_IN_MADRID) == [("run", "tu_dinero_es")]
    assert tick(tmp_path, TUESDAY_AFTER_NOON_IN_MADRID) == []


def test_the_channel_runs_again_the_next_day(tmp_path):
    tick(tmp_path, TUESDAY_AFTER_NOON_IN_MADRID)

    assert tick(tmp_path, WEDNESDAY_AFTER_NOON_IN_MADRID) == [("run", "tu_dinero_es")]


def test_mondays_also_send_the_weekly_digest(tmp_path):
    assert tick(tmp_path, MONDAY_AFTER_NOON_IN_MADRID) == [("run", "tu_dinero_es"), ("report", "tu_dinero_es")]


def test_a_channel_without_publish_settings_is_never_scheduled(tmp_path):
    assert tick(tmp_path, MONDAY_AFTER_NOON_IN_MADRID, profiles=(replace(PROFILE, publish=None),)) == []


def test_a_failing_job_is_not_retried_the_same_day(tmp_path):
    def broken(job):
        raise RuntimeError("boom")

    scheduler.tick((PROFILE,), tmp_path, TUESDAY_AFTER_NOON_IN_MADRID, broken)

    assert tick(tmp_path, TUESDAY_AFTER_NOON_IN_MADRID) == []


def test_every_tick_leaves_a_fresh_heartbeat(tmp_path):
    tick(tmp_path, TUESDAY_BEFORE_NOON_IN_MADRID)

    assert scheduler.heartbeat_age(tmp_path, datetime.now(timezone.utc)) < 60


def test_a_missing_heartbeat_counts_as_stale(tmp_path):
    assert scheduler.heartbeat_age(tmp_path, datetime.now(timezone.utc)) == float("inf")


def test_jobs_run_the_command_line_of_the_channel_with_a_time_limit():
    calls = []

    def runner(command, timeout, check):
        calls.append((command[-2:], timeout, check))
        return subprocess.CompletedProcess(command, 0)

    scheduler.execute(scheduler.Job("run", "tu_dinero_es", "2026-11-10"), runner=runner, alert=lambda text: True)

    assert calls == [(["run", "tu_dinero_es"], scheduler.JOB_TIMEOUT_SECONDS, False)]


def test_a_job_over_its_time_limit_alerts_the_owner():
    alerts = []

    def runner(command, timeout, check):
        raise subprocess.TimeoutExpired(command, timeout)

    scheduler.execute(scheduler.Job("run", "tu_dinero_es", "2026-11-10"), runner=runner, alert=alerts.append)

    assert "tu_dinero_es" in alerts[0] and "minutos" in alerts[0]


def test_the_healthcheck_fails_without_a_recent_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler, "runs_root", lambda: tmp_path)

    assert scheduler.healthcheck() == 1
    tick(tmp_path, TUESDAY_BEFORE_NOON_IN_MADRID)
    assert scheduler.healthcheck() == 0
