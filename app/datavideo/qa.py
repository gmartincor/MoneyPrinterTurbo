from dataclasses import dataclass
from pathlib import Path

from moviepy import VideoFileClip

from app.datavideo.audio import TARGET_LOUDNESS, measure_loudness
from app.datavideo.scenes.base import Size

LOUDNESS_TOLERANCE = 2.5
NARRATION_TOLERANCE_SECONDS = 0.5


@dataclass(frozen=True)
class DurationLimits:
    minimum_seconds: float
    maximum_seconds: float


SHORT_LIMITS = DurationLimits(minimum_seconds=15.0, maximum_seconds=180.0)


@dataclass(frozen=True)
class QualityReport:
    problems: tuple[str, ...]
    duration: float
    loudness: float | None

    @property
    def passed(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict:
        return {"passed": self.passed, "problems": list(self.problems), "duration": self.duration, "loudness": self.loudness}


def check_video(
    video_path: Path, expected_size: Size, narration_seconds: float, subtitle_path: Path, limits: DurationLimits
) -> QualityReport:
    problems = []
    with VideoFileClip(str(video_path)) as clip:
        size = tuple(clip.size)
        duration = float(clip.duration)
        has_audio = clip.audio is not None
    if size != tuple(expected_size):
        problems.append(f"video size is {size[0]}x{size[1]} instead of {expected_size[0]}x{expected_size[1]}")
    if not limits.minimum_seconds <= duration <= limits.maximum_seconds:
        problems.append(
            f"duration {duration:.1f} s is outside {limits.minimum_seconds:.0f}-{limits.maximum_seconds:.0f} s"
        )
    if abs(duration - narration_seconds) > NARRATION_TOLERANCE_SECONDS:
        problems.append(f"video lasts {duration:.1f} s but the narration lasts {narration_seconds:.1f} s")
    loudness = None
    if not has_audio:
        problems.append("video has no audio track")
    else:
        loudness = measure_loudness(video_path)
        if abs(loudness - TARGET_LOUDNESS) > LOUDNESS_TOLERANCE:
            problems.append(f"loudness is {loudness:.1f} LUFS instead of {TARGET_LOUDNESS:.0f} LUFS")
    if not subtitle_path.is_file() or subtitle_path.stat().st_size == 0:
        problems.append("subtitles are missing")
    return QualityReport(problems=tuple(problems), duration=duration, loudness=loudness)
