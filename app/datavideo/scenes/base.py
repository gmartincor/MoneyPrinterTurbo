import os
from typing import Protocol

import numpy as np
from moviepy import VideoClip
from PIL import Image, ImageFont

from app.datavideo.theme import Theme
from app.utils import utils

Size = tuple[int, int]
Box = tuple[int, int, int, int]

VERTICAL_SIZE = (1080, 1920)
HORIZONTAL_SIZE = (1920, 1080)
_GROWTH_SHARE_OF_DURATION = 0.4
_MAX_GROWTH_SECONDS = 1.5


class Scene(Protocol):
    def draw(self, size: Size, progress: float) -> Image.Image: ...


def ease_out(progress: float) -> float:
    clamped = min(1.0, max(0.0, progress))
    return 1 - (1 - clamped) ** 3


def load_font(theme: Theme, pixel_size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(utils.font_dir(), theme.font_file), max(8, pixel_size))


def render_scene_clip(
    scene: Scene,
    output_path: str,
    duration: float = 6.0,
    fps: int = 30,
    size: Size = VERTICAL_SIZE,
) -> str:
    growth_seconds = min(_MAX_GROWTH_SECONDS, duration * _GROWTH_SHARE_OF_DURATION)
    final_frame = np.array(scene.draw(size, 1.0))

    def frame_at(seconds: float) -> np.ndarray:
        if seconds >= growth_seconds:
            return final_frame
        return np.array(scene.draw(size, seconds / growth_seconds))

    clip = VideoClip(frame_function=frame_at, duration=duration)
    try:
        clip.write_videofile(output_path, fps=fps, codec="libx264", audio=False, logger=None)
    finally:
        clip.close()
    return output_path
