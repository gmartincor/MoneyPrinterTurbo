import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Sequence
from zoneinfo import ZoneInfo

from loguru import logger

from app.datavideo.channels import ChannelProfile, load_channels
from app.datavideo.digest import weekly_digest
from app.datavideo.editor import weakest
from app.datavideo.notify import send_alert
from app.datavideo.pipeline import BlockedPublication, Production, produce, publish
from app.datavideo.script import ScriptRejected
from app.datavideo.store import publications
from app.datavideo.stories.regional_ranking import STORIES

_NEVER = datetime.min.replace(tzinfo=timezone.utc)


@dataclass
class Outcome:
    lines: list[str] = field(default_factory=list)
    failed: bool = False

    def fail(self, profile: ChannelProfile, key: str, error: Exception, alert: Callable[[str], bool]) -> None:
        self.failed = True
        if isinstance(error, (BlockedPublication, ScriptRejected)):
            reason = "; ".join(error.problems) if isinstance(error, ScriptRejected) else str(error)
            self.lines.append(f"{profile.id}/{key}: blocked: {reason}")
            alert(f"Vídeo bloqueado en {profile.id} ({key}): {reason}")
            return
        logger.opt(exception=error).error(f"data video run failed: channel={profile.id} story={key}")
        self.lines.append(f"{profile.id}/{key}: failed: {type(error).__name__}: {error}")
        alert(f"Fallo en {profile.id} ({key}): {type(error).__name__}: {error}")


def run_channel(
    profile: ChannelProfile,
    publish_videos: bool,
    *,
    now: datetime | None = None,
    produce_story: Callable = produce,
    publish_production: Callable = publish,
    alert: Callable[[str], bool] = send_alert,
    published: Callable[[str], dict[str, dict]] = publications,
) -> Outcome:
    unknown = [key for key in profile.stories if key not in STORIES]
    if unknown:
        raise ValueError(f"channel {profile.id} lists unknown stories: {', '.join(unknown)}")
    outcome = Outcome()
    candidates = []
    for key in profile.stories:
        try:
            production = produce_story(profile, STORIES[key])
        except Exception as error:
            outcome.fail(profile, key, error, alert)
            continue
        if production is None:
            outcome.lines.append(f"{profile.id}/{key}: no new data to publish")
            continue
        outcome.lines.append(f"{profile.id}/{production.run.story_key}: video {production.video_path}")
        candidates.append(production)
    if publish_videos and candidates:
        _publish_due(profile, candidates, now or datetime.now(timezone.utc), outcome, publish_production, alert, published)
    return outcome


def _publish_due(
    profile: ChannelProfile,
    candidates: list[Production],
    now: datetime,
    outcome: Outcome,
    publish_production: Callable,
    alert: Callable[[str], bool],
    published: Callable[[str], dict[str, dict]],
) -> None:
    settings = profile.publish
    if settings is None:
        outcome.fail(profile, "publish", BlockedPublication(f"channel {profile.id} has no publish settings"), alert)
        return
    zone = ZoneInfo(settings.timezone)
    records = list(published(profile.id).values())
    today = now.astimezone(zone).date()
    remaining = settings.per_day - sum(_published_at(record).astimezone(zone).date() == today for record in records)
    last_by_table: dict[int, datetime] = {}
    for record in records:
        story = STORIES.get(record.get("story", ""))
        if story is not None:
            last_by_table[story.table_id] = max(last_by_table.get(story.table_id, _NEVER), _published_at(record))
    ordered = sorted(
        candidates,
        key=lambda item: (
            last_by_table.get(item.story.table_id, _NEVER),
            -item.review.total,
            profile.stories.index(item.story.key),
        ),
    )
    for production in ordered:
        story_key = production.run.story_key
        if not production.review.publishable:
            outcome.lines.append(f"{profile.id}/{story_key}: held by the editor: {weakest(production.review.scores)}")
            continue
        if remaining <= 0:
            outcome.lines.append(f"{profile.id}/{story_key}: queued for a later day")
            continue
        try:
            record = publish_production(production, profile)
        except Exception as error:
            outcome.fail(profile, story_key, error, alert)
            continue
        remaining -= 1
        outcome.lines.append(f"{profile.id}/{story_key}: published, request_id {record.get('request_id')}")


def _published_at(record: dict) -> datetime:
    return datetime.fromisoformat(record["published_at"])


def main(argv: Sequence[str] | None = None) -> int:
    profiles = load_channels()
    parser = argparse.ArgumentParser(prog="python -m app.datavideo.cli")
    parser.add_argument(
        "command", choices=["produce", "run", "report"], help="produce only, produce and publish, or send the weekly digest"
    )
    parser.add_argument("channel", choices=sorted(profiles))
    arguments = parser.parse_args(argv)
    if arguments.command == "report":
        digest = weekly_digest(arguments.channel, datetime.now(timezone.utc))
        print(digest)
        send_alert(digest)
        return 0
    outcome = run_channel(profiles[arguments.channel], publish_videos=arguments.command == "run")
    for line in outcome.lines:
        print(line)
    return 1 if outcome.failed else 0


if __name__ == "__main__":
    sys.exit(main())
