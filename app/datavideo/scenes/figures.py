import re
from dataclasses import dataclass

from PIL import Image, ImageDraw

from app.datavideo.facts import Fact
from app.datavideo.scenes.base import Size, blend, content_box, ease_out, fitting_font, load_font, short_side, wrap_lines
from app.datavideo.theme import Color, Theme

_FIRST_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_THOUSANDS_DIGITS = 3



def counting_value(value: str, amount: float) -> str:
    match = _FIRST_NUMBER.search(value)
    if amount >= 1 or match is None:
        return value
    number = match.group()
    separator = "," if "," in number else "." if "." in number else ""
    fraction = number.partition(separator)[2] if separator else ""
    grouped = separator == "." and len(fraction) == _THOUSANDS_DIGITS
    places = 0 if grouped or not separator else len(fraction)
    target = float(number.replace(".", "").replace(",", ".")) if grouped or separator == "," else float(number)
    shown = f"{target * max(0.0, amount):.{places}f}"
    shown = shown.replace(".", ",") if separator == "," else shown
    return f"{value[: match.start()]}{shown}{value[match.end():]}"


def _draw_lines(
    draw: ImageDraw.ImageDraw, lines: list[str], center_x: float, top: float, font, fill: Color
) -> float:
    line_height = font.size * 1.25
    for index, line in enumerate(lines):
        draw.text((center_x, top + index * line_height), line, font=font, fill=fill, anchor="mt")
    return top + len(lines) * line_height


@dataclass(frozen=True)
class BigNumberScene:
    fact: Fact
    color: Color
    theme: Theme
    counting: bool = True

    def draw(self, size: Size, progress: float) -> Image.Image:
        image = Image.new("RGB", size, self.theme.background)
        draw = ImageDraw.Draw(image)
        left, top, right, bottom = content_box(size)
        width = right - left
        center_x = (left + right) / 2
        amount = ease_out(progress)
        label_font = load_font(self.theme, round(short_side(size) * 0.055))
        value_font = fitting_font(draw, [self.fact.value], self.theme, round(short_side(size) * 0.32), width)
        detail_font = load_font(self.theme, round(short_side(size) * 0.05))
        label_lines = wrap_lines(draw, self.fact.label, label_font, width)
        detail_lines = wrap_lines(draw, self.fact.detail, detail_font, width) if self.fact.detail else []
        block_height = (
            len(label_lines) * label_font.size * 1.25
            + value_font.size * 1.3
            + len(detail_lines) * detail_font.size * 1.25
        )
        y = top + max(0.0, (bottom - top - block_height) / 2)
        y = _draw_lines(draw, label_lines, center_x, y, label_font, blend(self.theme.background, self.theme.muted, amount))
        draw.text(
            (center_x, y + value_font.size * 0.1),
            counting_value(self.fact.value, amount) if self.counting else self.fact.value,
            font=value_font,
            fill=blend(self.theme.background, self.color, amount),
            anchor="mt",
        )
        y += value_font.size * 1.3
        _draw_lines(draw, detail_lines, center_x, y, detail_font, blend(self.theme.background, self.theme.text, amount))
        return image
