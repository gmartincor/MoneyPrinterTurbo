import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

from loguru import logger

from app.datavideo.channels import ChannelProfile, load_channels
from app.datavideo.notify import send_alert
from app.datavideo.store import Run, runs_root

JOB_TIMEOUT_SECONDS = 90 * 60
TICK_SECONDS = 60
HEARTBEAT_FILE = "heartbeat"
STATE_FILE = "scheduler.json"
_REPORT_WEEKDAY = 0


@dataclass(frozen=True)
class Job:
    command: str
    channel: str
    day: str

    @property
    def key(self) -> str:
        return f"{self.command}:{self.channel}"


def due_jobs(profiles: Iterable[ChannelProfile], done: dict[str, str], now: datetime) -> list[Job]:
    jobs = []
    for profile in profiles:
        if profile.publish is None:
            continue
        local = now.astimezone(ZoneInfo(profile.publish.timezone))
        if local.strftime("%H:%M") < profile.publish.daily_at:
            continue
        day = local.date().isoformat()
        commands = ["run", "report"] if local.weekday() == _REPORT_WEEKDAY else ["run"]
        jobs += [Job(command, profile.id, day) for command in commands if done.get(f"{command}:{profile.id}") != day]
    return jobs


def tick(profiles: Iterable[ChannelProfile], root: Path, now: datetime, run_job: Callable[[Job], None]) -> list[Job]:
    state = Run(directory=root)
    done = state.read_json(STATE_FILE) if state.has(STATE_FILE) else {}
    jobs = due_jobs(profiles, done, now)
    for job in jobs:
        logger.info(f"data video job started: {job.key}")
        try:
            run_job(job)
        except Exception:
            logger.exception(f"data video job crashed: {job.key}")
        done[job.key] = job.day
        state.write_json(STATE_FILE, done)
    state.path(HEARTBEAT_FILE).write_text(now.isoformat(timespec="seconds"), encoding="utf-8")
    return jobs


def heartbeat_age(root: Path, now: datetime) -> float:
    heartbeat = root / HEARTBEAT_FILE
    if not heartbeat.is_file():
        return float("inf")
    return now.timestamp() - heartbeat.stat().st_mtime


def execute(
    job: Job,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    alert: Callable[[str], bool] = send_alert,
) -> None:
    command = [sys.executable, "-m", "app.datavideo.cli", job.command, job.channel]
    try:
        finished = runner(command, timeout=JOB_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        alert(f"Fallo en {job.channel}: «{job.command}» superó {JOB_TIMEOUT_SECONDS // 60} minutos y se canceló")
        return
    logger.info(f"data video job finished: {job.key} exit={finished.returncode}")


def main() -> None:
    root = runs_root()
    root.mkdir(parents=True, exist_ok=True)
    logger.info(f"data video scheduler started: root={root}")
    while True:
        try:
            tick(load_channels().values(), root, datetime.now(timezone.utc), execute)
        except Exception:
            logger.exception("data video scheduler tick failed")
        time.sleep(TICK_SECONDS)


def healthcheck() -> int:
    return 0 if heartbeat_age(runs_root(), datetime.now(timezone.utc)) < 2 * JOB_TIMEOUT_SECONDS else 1


if __name__ == "__main__":
    sys.exit(healthcheck() if sys.argv[1:] == ["healthcheck"] else main())
