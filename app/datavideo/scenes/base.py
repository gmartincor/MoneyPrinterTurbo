import os
from dataclasses import dataclass
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

from app.datavideo.theme import Color, Theme
from app.utils import utils

Size = tuple[int, int]
Box = tuple[int, int, int, int]

VERTICAL_SIZE = (1080, 1920)
HORIZONTAL_SIZE = (1920, 1080)
_VERTICAL_CONTENT_SHARES = (0.07, 0.15, 0.93, 0.68)
_HORIZONTAL_CONTENT_SHARES = (0.06, 0.17, 0.94, 0.80)
_HEADER_TITLE_SHARE = 0.055
_HEADER_SUBTITLE_SHARE = 0.032
_CREDIT_GAP_SHARE = 0.03
_CREDIT_FONT_SHARE = 0.03


class Scene(Protocol):
    def draw(self, size: Size, progress: float) -> Image.Image: ...


def ease_out(progress: float) -> float:
    clamped = min(1.0, max(0.0, progress))
    return 1 - (1 - clamped) ** 3


def blend(start: Color, end: Color, amount: float) -> Color:
    share = min(1.0, max(0.0, amount))
    return tuple(round(a + (b - a) * share) for a, b in zip(start, end))


def short_side(size: Size) -> int:
    return min(size)


def content_box(size: Size) -> Box:
    width, height = size
    shares = _VERTICAL_CONTENT_SHARES if height > width else _HORIZONTAL_CONTENT_SHARES
    left, top, right, bottom = shares
    return round(width * left), round(height * top), round(width * right), round(height * bottom)


def load_font(theme: Theme, pixel_size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(utils.font_dir(), theme.font_file), max(8, pixel_size))


def fitting_font(
    draw: ImageDraw.ImageDraw, texts: list[str], theme: Theme, pixel_size: int, max_width: float
) -> ImageFont.FreeTypeFont:
    size = pixel_size
    font = load_font(theme, size)
    while size > 8 and max(draw.textlength(text, font=font) for text in texts) > max_width:
        size -= 2
        font = load_font(theme, size)
    return font


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
    lines: list[str] = []
    for word in text.split():
        candidate = f"{lines[-1]} {word}" if lines else word
        if lines and draw.textlength(candidate, font=font) <= max_width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def draw_header(
    draw: ImageDraw.ImageDraw, size: Size, theme: Theme, title: str, subtitle: str, amount: float = 1.0
) -> None:
    width, height = size
    box_left, box_top, box_right, _ = content_box(size)
    max_width = box_right - box_left
    title_font = fitting_font(draw, [title], theme, round(short_side(size) * _HEADER_TITLE_SHARE), max_width)
    subtitle_font = load_font(theme, round(short_side(size) * _HEADER_SUBTITLE_SHARE))
    title_y = box_top - round(short_side(size) * 0.13)
    draw.text((width / 2, title_y), title, font=title_font, fill=blend(theme.background, theme.text, amount), anchor="mm")
    draw.text(
        (width / 2, title_y + title_font.size * 1.15),
        subtitle,
        font=subtitle_font,
        fill=blend(theme.background, theme.muted, amount),
        anchor="mm",
    )


@dataclass(frozen=True)
class CreditedScene:
    scene: Scene
    credit: str
    theme: Theme

    def draw(self, size: Size, progress: float) -> Image.Image:
        image = self.scene.draw(size, progress)
        draw = ImageDraw.Draw(image)
        font = load_font(self.theme, round(short_side(size) * _CREDIT_FONT_SHARE))
        y = content_box(size)[3] + short_side(size) * _CREDIT_GAP_SHARE
        draw.text((size[0] / 2, y), self.credit, font=font, fill=self.theme.muted, anchor="mm")
        return image
