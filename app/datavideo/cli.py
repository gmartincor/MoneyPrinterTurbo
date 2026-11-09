import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Sequence

from loguru import logger

from app.datavideo.channels import ChannelProfile, load_channels
from app.datavideo.digest import weekly_digest
from app.datavideo.notify import send_alert
from app.datavideo.pipeline import BlockedPublication, produce, publish
from app.datavideo.script import ScriptRejected
from app.datavideo.stories.regional_ranking import STORIES


@dataclass
class Outcome:
    lines: list[str] = field(default_factory=list)
    failed: bool = False


def run_channel(
    profile: ChannelProfile,
    publish_videos: bool,
    *,
    produce_story: Callable = produce,
    publish_production: Callable = publish,
    alert: Callable[[str], bool] = send_alert,
) -> Outcome:
    unknown = [key for key in profile.stories if key not in STORIES]
    if unknown:
        raise ValueError(f"channel {profile.id} lists unknown stories: {', '.join(unknown)}")
    outcome = Outcome()
    for key in profile.stories:
        try:
            production = produce_story(profile, STORIES[key])
            if production is None:
                outcome.lines.append(f"{profile.id}/{key}: no new data to publish")
                continue
            outcome.lines.append(f"{profile.id}/{production.run.story_key}: video {production.video_path}")
            if publish_videos:
                record = publish_production(production, profile)
                outcome.lines.append(
                    f"{profile.id}/{production.run.story_key}: published, request_id {record.get('request_id')}"
                )
        except (BlockedPublication, ScriptRejected) as error:
            outcome.failed = True
            reason = "; ".join(error.problems) if isinstance(error, ScriptRejected) else str(error)
            outcome.lines.append(f"{profile.id}/{key}: blocked: {reason}")
            alert(f"Vídeo bloqueado en {profile.id} ({key}): {reason}")
        except Exception as error:
            outcome.failed = True
            logger.exception(f"data video run failed: channel={profile.id} story={key}")
            outcome.lines.append(f"{profile.id}/{key}: failed: {type(error).__name__}: {error}")
            alert(f"Fallo en {profile.id} ({key}): {type(error).__name__}: {error}")
    return outcome


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
