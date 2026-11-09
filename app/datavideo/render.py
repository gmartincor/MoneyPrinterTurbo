from bisect import bisect_right
from dataclasses import dataclass
from itertools import accumulate
from pathlib import Path
from typing import Sequence

import numpy as np
from moviepy import VideoClip

from app.datavideo.scenes.base import Scene, Size
from app.datavideo.theme import Theme
from app.datavideo.timeline import Narration
from app.models.schema import VideoParams
from app.services import video

FPS = 30
_GROWTH_SHARE_OF_DURATION = 0.4
_MAX_GROWTH_SECONDS = 1.2
_SUBTITLE_POSITION_PERCENT = 84.0
_SUBTITLE_FONT_SIZE = 60
_SUBTITLE_STROKE_WIDTH = 2.0
_THREADS = 4


@dataclass(frozen=True)
class TimedScene:
    scene: Scene
    duration: float


def render_scene_track(timed_scenes: Sequence[TimedScene], output_path: Path, size: Size, fps: int = FPS) -> Path:
    starts = [0.0, *accumulate(item.duration for item in timed_scenes)][:-1]
    total = sum(item.duration for item in timed_scenes)
    final_frames = [np.array(item.scene.draw(size, 1.0)) for item in timed_scenes]

    def frame_at(seconds: float) -> np.ndarray:
        index = min(max(bisect_right(starts, seconds) - 1, 0), len(timed_scenes) - 1)
        item = timed_scenes[index]
        growth = min(_MAX_GROWTH_SECONDS, item.duration * _GROWTH_SHARE_OF_DURATION)
        local = seconds - starts[index]
        if local >= growth:
            return final_frames[index]
        return np.array(item.scene.draw(size, local / growth))

    clip = VideoClip(frame_function=frame_at, duration=total)
    try:
        clip.write_videofile(str(output_path), fps=fps, codec="libx264", audio=False, logger=None)
    finally:
        clip.close()
    return output_path


def compose_video(
    scene_track: Path, narration: Narration, output_path: Path, aspect: str, title: str, theme: Theme
) -> Path:
    has_subtitles = narration.subtitle_path.exists()
    params = VideoParams(
        video_subject=title,
        video_aspect=aspect,
        subtitle_enabled=has_subtitles,
        subtitle_position="custom",
        custom_position=_SUBTITLE_POSITION_PERCENT,
        font_name=theme.font_file,
        font_size=_SUBTITLE_FONT_SIZE,
        text_fore_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=_SUBTITLE_STROKE_WIDTH,
        bgm_type="",
        voice_volume=1.0,
        n_threads=_THREADS,
    )
    video.generate_video(
        video_path=str(scene_track),
        audio_path=str(narration.audio_path),
        subtitle_path=str(narration.subtitle_path) if has_subtitles else "",
        output_file=str(output_path),
        params=params,
    )
    return output_path
