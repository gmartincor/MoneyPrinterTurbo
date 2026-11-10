from dataclasses import dataclass

from PIL import Image, ImageDraw

from app.datavideo.facts import Fact, Source
from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.scenes.base import Size, blend, content_box, ease_out, fitting_font, load_font, short_side, wrap_lines
from app.datavideo.theme import Color, Theme

_SOURCE_TEXT = {
    SPANISH_SPAIN: {
        "heading": "Fuente",
        "period": "Datos: {period}",
        "disclosure": "Guion generado con IA a partir de datos oficiales",
    },
    "en-US": {
        "heading": "Source",
        "period": "Data: {period}",
        "disclosure": "Script generated with AI from official data",
    },
}


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

    def draw(self, size: Size, progress: float) -> Image.Image:
        image = Image.new("RGB", size, self.theme.background)
        draw = ImageDraw.Draw(image)
        left, top, right, bottom = content_box(size)
        width = right - left
        center_x = (left + right) / 2
        amount = ease_out(progress)
        label_font = load_font(self.theme, round(short_side(size) * 0.055))
        value_font = fitting_font(draw, [self.fact.value], self.theme, round(short_side(size) * 0.24), width)
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
            self.fact.value,
            font=value_font,
            fill=blend(self.theme.background, self.color, amount),
            anchor="mt",
        )
        y += value_font.size * 1.3
        _draw_lines(draw, detail_lines, center_x, y, detail_font, blend(self.theme.background, self.theme.text, amount))
        return image


@dataclass(frozen=True)
class SourceCardScene:
    source: Source
    period: str
    locale: str
    theme: Theme

    def draw(self, size: Size, progress: float) -> Image.Image:
        image = Image.new("RGB", size, self.theme.background)
        draw = ImageDraw.Draw(image)
        text = _SOURCE_TEXT[self.locale]
        left, top, right, bottom = content_box(size)
        width = right - left
        center_x = (left + right) / 2
        amount = ease_out(progress)
        muted = blend(self.theme.background, self.theme.muted, amount)
        heading_font = load_font(self.theme, round(short_side(size) * 0.05))
        name_font = fitting_font(draw, [self.source.name], self.theme, round(short_side(size) * 0.18), width)
        body_font = load_font(self.theme, round(short_side(size) * 0.042))
        attribution = wrap_lines(draw, self.source.attribution or self.source.url, body_font, width)
        period = text["period"].format(period=self.period)
        disclosure = wrap_lines(draw, text["disclosure"], body_font, width)
        y = top + (bottom - top) * 0.12
        y = _draw_lines(draw, [text["heading"]], center_x, y, heading_font, muted)
        draw.text((center_x, y), self.source.name, font=name_font, fill=blend(self.theme.background, self.theme.text, amount), anchor="mt")
        y += name_font.size * 1.4
        y = _draw_lines(draw, attribution, center_x, y, body_font, blend(self.theme.background, self.theme.text, amount))
        y = _draw_lines(draw, [period], center_x, y + body_font.size, body_font, muted)
        _draw_lines(draw, disclosure, center_x, y + body_font.size, body_font, muted)
        return image
