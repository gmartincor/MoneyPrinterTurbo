from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.datavideo.audio import normalize_loudness
from app.datavideo.channels import ChannelProfile, text_generator
from app.datavideo.facts import Fact, unique_sources
from app.datavideo.packaging import Package, build_package
from app.datavideo.publish import publish_video
from app.datavideo.qa import SHORT_LIMITS, QualityReport, check_video
from app.datavideo.render import TimedScene, compose_video, render_scene_track
from app.datavideo.scenes.base import VERTICAL_SIZE, CreditedScene, Size
from app.datavideo.scenes.catalog import FACT_SCENES, SCENE_DESCRIPTIONS, SceneContext, build_scene, credit_line
from app.datavideo.script import Script, generate_verified_script, script_from_dict, script_to_dict
from app.datavideo.sources.ine import INE_SOURCE, download_table, parse_table
from app.datavideo.store import PUBLICATION_FILE, Run, open_run, published_story_keys
from app.datavideo.stories.regional_ranking import (
    PERIODS_TO_DOWNLOAD,
    RegionalRanking,
    RegionalRankingStory,
    build_ranking,
    describe_ranking,
)
from app.datavideo.timeline import SUBTITLE_FILE_NAME, Narration, narrate
from app.services import upload_post

SOURCE_FILE = "source.json"
FACTS_FILE = "facts.json"
SCRIPT_FILE = "script.json"
TIMELINE_FILE = "timeline.json"
VOICE_FILE = "voice.mp3"
SCENES_FILE = "scenes.mp4"
FINAL_FILE = "final.mp4"
QUALITY_FILE = "quality.json"
PACKAGE_FILE = "package.json"
SHORT_ASPECT = "9:16"


class BlockedPublication(Exception):
    pass


@dataclass(frozen=True)
class Production:
    run: Run
    story: RegionalRankingStory
    video_path: Path
    script: Script
    facts: tuple[Fact, ...]
    package: Package
    quality: QualityReport


def produce(
    profile: ChannelProfile,
    story: RegionalRankingStory,
    *,
    root: Path | None = None,
    download: Callable[[int, int], Any] = download_table,
    generate: Callable[[str], str] | None = None,
    size: Size = VERTICAL_SIZE,
) -> Production | None:
    payload = download(story.table_id, PERIODS_TO_DOWNLOAD)
    ranking = build_ranking(parse_table(payload), story)
    if ranking.story_key in published_story_keys(profile.id, root):
        return None
    run = open_run(profile.id, ranking.story_key, root)
    _keep_source(run, story, payload)
    facts = tuple(describe_ranking(ranking, story))
    run.write_json(FACTS_FILE, [{"key": fact.key, "statement": fact.statement, "source": fact.source.name} for fact in facts])
    script = _script(run, profile, story, facts, generate)
    narration = _narration(run, profile, script)
    final = run.path(FINAL_FILE)
    if not run.has(FINAL_FILE):
        scene_track = _scene_track(run, profile, ranking, facts, script, narration, size)
        compose_video(scene_track, narration, run.partial_path(FINAL_FILE), SHORT_ASPECT, script.title, profile.theme)
        run.commit(FINAL_FILE)
    quality = check_video(final, size, sum(narration.durations), narration.subtitle_path, SHORT_LIMITS)
    run.write_json(QUALITY_FILE, quality.to_dict())
    package = build_package(script, facts, ranking.period_label(profile.language), story.tags, profile.language)
    run.write_json(PACKAGE_FILE, {"title": package.title, "description": package.description, "tags": list(package.tags)})
    return Production(run=run, story=story, video_path=final, script=script, facts=facts, package=package, quality=quality)


def publish(
    production: Production, profile: ChannelProfile, cross_post: Callable[..., dict] = upload_post.cross_post_video
) -> dict:
    run = production.run
    if run.has(PUBLICATION_FILE):
        previous = run.read_json(PUBLICATION_FILE)
        if previous.get("success") is True:
            return previous
        raise BlockedPublication(
            f"an earlier upload of {run.story_key} was not confirmed (request_id {previous.get('request_id')}); "
            "check Upload-Post before publishing again"
        )
    if profile.publish is None:
        raise BlockedPublication(f"channel {profile.id} has no publish settings")
    unverified = sorted({fact.source.name for fact in production.facts if not fact.source.license_verified})
    if unverified:
        raise BlockedPublication(f"licence not verified for: {', '.join(unverified)}")
    if not production.quality.passed:
        raise BlockedPublication(f"technical checks failed: {'; '.join(production.quality.problems)}")

    def upload_with_pending_record(**arguments: Any) -> dict:
        run.write_json(PUBLICATION_FILE, {"success": False, "request_id": None, "error": "upload started, no reply yet"})
        return cross_post(**arguments)

    result = publish_video(production.video_path, production.package, profile.publish, cross_post=upload_with_pending_record)
    record = {
        "success": result.get("success") is True,
        "request_id": result.get("request_id"),
        "story": production.story.key,
        "user": profile.publish.user,
        "platforms": list(profile.publish.platforms),
        "privacy": profile.publish.privacy,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "error": result.get("error"),
    }
    run.write_json(PUBLICATION_FILE, record)
    if not record["success"]:
        raise RuntimeError(f"upload of {run.story_key} failed: {record['error']}")
    return record


def _keep_source(run: Run, story: RegionalRankingStory, payload: Any) -> None:
    if run.has(SOURCE_FILE):
        return
    run.write_json(
        SOURCE_FILE,
        {
            "source": INE_SOURCE.name,
            "table_id": story.table_id,
            "license": INE_SOURCE.license,
            "license_verified": INE_SOURCE.license_verified,
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "payload": payload,
        },
    )


def _script(
    run: Run,
    profile: ChannelProfile,
    story: RegionalRankingStory,
    facts: tuple[Fact, ...],
    generate: Callable[[str], str] | None,
) -> Script:
    if run.has(SCRIPT_FILE):
        return script_from_dict(run.read_json(SCRIPT_FILE))
    script = generate_verified_script(
        facts,
        story.topic,
        profile.language,
        SCENE_DESCRIPTIONS,
        generate or text_generator(profile, "writer"),
        fact_scenes=FACT_SCENES,
    )
    run.write_json(SCRIPT_FILE, script_to_dict(script))
    return script


def _narration(run: Run, profile: ChannelProfile, script: Script) -> Narration:
    subtitle_path = run.path(SUBTITLE_FILE_NAME)
    if run.has(TIMELINE_FILE) and run.has(VOICE_FILE):
        durations = tuple(run.read_json(TIMELINE_FILE)["durations"])
        return Narration(audio_path=run.path(VOICE_FILE), subtitle_path=subtitle_path, durations=durations)
    spoken = narrate([segment.text for segment in script.segments], profile.voice.name, profile.voice.rate, run.directory)
    normalize_loudness(spoken.audio_path, run.path(VOICE_FILE))
    run.write_json(TIMELINE_FILE, {"durations": list(spoken.durations)})
    return Narration(audio_path=run.path(VOICE_FILE), subtitle_path=spoken.subtitle_path, durations=spoken.durations)


def _scene_track(
    run: Run,
    profile: ChannelProfile,
    ranking: RegionalRanking,
    facts: tuple[Fact, ...],
    script: Script,
    narration: Narration,
    size: Size,
) -> Path:
    track = run.path(SCENES_FILE)
    if run.has(SCENES_FILE):
        return track
    context = SceneContext(
        ranking=ranking, facts={fact.key: fact for fact in facts}, theme=profile.theme, locale=profile.language
    )
    credit = credit_line(unique_sources(facts)[0], ranking.period_label(profile.language), profile.language)
    timed = [
        TimedScene(CreditedScene(build_scene(segment.scene, segment.fact_keys, context), credit, profile.theme), duration)
        for segment, duration in zip(script.segments, narration.durations)
    ]
    render_scene_track(timed, run.partial_path(SCENES_FILE), size)
    return run.commit(SCENES_FILE)
