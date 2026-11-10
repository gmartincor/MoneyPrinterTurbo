from dataclasses import dataclass
from decimal import Decimal

from PIL import Image, ImageDraw, ImageFont

from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.scenes.base import Box, Size, blend, content_box, draw_header, ease_out, fitting_font, load_font
from app.datavideo.stories.regional_ranking import RegionalRanking, RegionalValue, format_value
from app.datavideo.theme import Color, Theme

_TEXT = {
    SPANISH_SPAIN: {"title": "{indicator} por comunidades", "national": "España"},
    "en-US": {"title": "{indicator} by region", "national": "National"},
}
_NAME_COLUMN_SHARE = 0.36
_VALUE_COLUMN_SHARE = 0.16
_BAR_HEIGHT_SHARE = 0.64
_LABEL_GAP_SHARE = 0.012
_LABEL_OFFSET_SHARE = 0.2
_LABEL_PADDING_SHARE = 0.08
_DIMMED_SHARE = 0.3


def extreme_colors(ranking: RegionalRanking, theme: Theme) -> tuple[Color, Color]:
    if ranking.story.higher_is_better:
        return theme.positive, theme.negative
    return theme.negative, theme.positive


@dataclass(frozen=True)
class _Columns:
    names_right: float
    bar_left: float
    bar_right: float
    top: float
    row_height: float
    low: Decimal
    span: Decimal
    font: ImageFont.FreeTypeFont

    def x_of(self, value: Decimal) -> float:
        return self.bar_left + float((value - self.low) / self.span) * (self.bar_right - self.bar_left)


@dataclass(frozen=True)
class RankingScene:
    ranking: RegionalRanking
    theme: Theme
    locale: str
    focus: frozenset[str] = frozenset()

    def _columns(self, size: Size) -> _Columns:
        left, top, right, bottom = content_box(size)
        width = right - left
        values = [item.value for item in self.ranking.regions] + [self.ranking.national]
        low = min([Decimal(0), *values])
        high = max([Decimal(0), *values])
        row_height = (bottom - top) / len(self.ranking.regions)
        names_right = left + width * _NAME_COLUMN_SHARE - width * _LABEL_GAP_SHARE
        measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        font = fitting_font(
            measure, [item.region for item in self.ranking.regions], self.theme, round(row_height * 0.5), names_right - left
        )
        widest_label = max(measure.textlength(self._value_text(value), font=font) for value in values)
        label_space = widest_label + row_height * (_LABEL_OFFSET_SHARE + _LABEL_PADDING_SHARE) + 1
        return _Columns(
            names_right=names_right,
            bar_left=left + width * _NAME_COLUMN_SHARE,
            bar_right=right - max(width * _VALUE_COLUMN_SHARE, label_space),
            top=top,
            row_height=row_height,
            low=low,
            span=(high - low) or Decimal(1),
            font=font,
        )

    def bar_boxes(self, size: Size, progress: float) -> list[Box]:
        columns = self._columns(size)
        zero_x = columns.x_of(Decimal(0))
        growth = ease_out(progress)
        bar_height = columns.row_height * _BAR_HEIGHT_SHARE
        boxes = []
        for index, item in enumerate(self.ranking.regions):
            end_x = zero_x + (columns.x_of(item.value) - zero_x) * growth
            top = columns.top + index * columns.row_height + (columns.row_height - bar_height) / 2
            boxes.append((round(min(zero_x, end_x)), round(top), round(max(zero_x, end_x)), round(top + bar_height)))
        return boxes

    def draw(self, size: Size, progress: float) -> Image.Image:
        image = Image.new("RGB", size, self.theme.background)
        draw = ImageDraw.Draw(image)
        text = _TEXT[self.locale]
        draw_header(
            draw,
            size,
            self.theme,
            text["title"].format(indicator=self.ranking.story.indicator),
            self.ranking.period_label(self.locale),
        )
        columns = self._columns(size)
        boxes = self.bar_boxes(size, progress)
        name_font = columns.font
        for item, box in zip(self.ranking.regions, boxes):
            middle_y = (box[1] + box[3]) / 2
            draw.text((columns.names_right, middle_y), item.region, font=name_font, fill=self._dimmed(item, self.theme.text), anchor="rm")
            if box[2] > box[0]:
                draw.rectangle(box, fill=self._bar_color(item))
        self._draw_national_line(draw, size, columns, text["national"])
        if progress >= 1.0:
            for item, box in zip(self.ranking.regions, self.bar_boxes(size, 1.0)):
                self._draw_value_label(draw, item, box, name_font, columns.row_height)
        return image

    def value_label_box(self, size: Size, index: int) -> Box:
        image = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(image)
        columns = self._columns(size)
        box = self.bar_boxes(size, 1.0)[index]
        return self._label_box(draw, self.ranking.regions[index], box, columns.font, columns.row_height)

    def _label_box(self, draw: ImageDraw.ImageDraw, item: RegionalValue, bar: Box, font, row_height: float) -> Box:
        anchor_point = (bar[2] + row_height * _LABEL_OFFSET_SHARE, (bar[1] + bar[3]) / 2)
        left, top, right, bottom = draw.textbbox(anchor_point, self._value_text(item.value), font=font, anchor="lm")
        padding = round(row_height * _LABEL_PADDING_SHARE)
        return left - padding, top - padding, right + padding, bottom + padding

    def _draw_value_label(self, draw: ImageDraw.ImageDraw, item: RegionalValue, bar: Box, font, row_height: float) -> None:
        box = self._label_box(draw, item, bar, font, row_height)
        draw.rectangle(box, fill=self.theme.background)
        anchor_point = (bar[2] + row_height * _LABEL_OFFSET_SHARE, (bar[1] + bar[3]) / 2)
        draw.text(anchor_point, self._value_text(item.value), font=font, fill=self._dimmed(item, self.theme.text), anchor="lm")

    def _value_text(self, value: Decimal) -> str:
        return format_value(self.ranking.story, value, self.locale)

    def _bar_color(self, item: RegionalValue) -> Color:
        highest_color, lowest_color = extreme_colors(self.ranking, self.theme)
        if item in self.ranking.highest:
            return self._dimmed(item, highest_color)
        if item in self.ranking.lowest:
            return self._dimmed(item, lowest_color)
        return self._dimmed(item, self.theme.neutral)

    def _dimmed(self, item: RegionalValue, color: Color) -> Color:
        if not self.focus or item.region in self.focus:
            return color
        return blend(self.theme.background, color, _DIMMED_SHARE)

    def _draw_national_line(self, draw: ImageDraw.ImageDraw, size: Size, columns: _Columns, label: str) -> None:
        x = columns.x_of(self.ranking.national)
        _, top, _, bottom = content_box(size)
        dash = max(4, round(columns.row_height * 0.25))
        for y in range(top, bottom, dash * 2):
            draw.line((x, y, x, min(y + dash, bottom)), fill=self.theme.muted, width=max(2, dash // 4))
        font = load_font(self.theme, round(columns.row_height * 0.45))
        caption = f"{label} {self._value_text(self.ranking.national)}"
        draw.text((x, top - columns.row_height * 0.3), caption, font=font, fill=self.theme.muted, anchor="mb")
