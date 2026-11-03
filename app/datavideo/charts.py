import os
from dataclasses import dataclass

import numpy as np
from moviepy import VideoClip
from PIL import Image, ImageDraw, ImageFont

from app.datavideo.electricity import (
    DailyElectricitySummary,
    HourlyPrice,
    format_eur_per_kwh,
    local_hour_label,
)
from app.datavideo.locale import SPANISH_SPAIN, format_long_date
from app.utils import utils

Color = tuple[int, int, int]
Box = tuple[int, int, int, int]

VERTICAL_SIZE = (1080, 1920)
TITLE = "Precio de la luz"
CHEAPEST_LABEL = "Más barata"
MOST_EXPENSIVE_LABEL = "Más cara"
_HOUR_LABEL_STEP = 6
_GROWTH_SHARE_OF_DURATION = 0.4
_MAX_GROWTH_SECONDS = 1.5


@dataclass(frozen=True)
class ChartTheme:
    background: Color = (14, 17, 23)
    bar: Color = (88, 101, 122)
    cheapest: Color = (46, 204, 113)
    most_expensive: Color = (231, 76, 60)
    text: Color = (240, 242, 245)
    muted: Color = (150, 160, 175)
    font_file: str = "BeVietnamPro-Bold.ttf"


DEFAULT_THEME = ChartTheme()


@dataclass(frozen=True)
class _Layout:
    width: int
    height: int

    @property
    def margin_x(self) -> int:
        return round(self.width * 0.08)

    @property
    def chart_top(self) -> int:
        return round(self.height * 0.30)

    @property
    def baseline(self) -> int:
        return round(self.height * 0.66)

    def font_size(self, share_of_width: float) -> int:
        return max(8, round(self.width * share_of_width))


def bar_boxes(
    summary: DailyElectricitySummary,
    size: tuple[int, int] = VERTICAL_SIZE,
    progress: float = 1.0,
) -> list[Box]:
    layout = _Layout(*size)
    slot_width = (layout.width - 2 * layout.margin_x) / len(summary.prices)
    bar_width = slot_width * 0.7
    tallest = max(price.eur_per_mwh for price in summary.prices)
    available_height = layout.baseline - layout.chart_top
    growth = _ease_out(progress)
    boxes = []
    for index, price in enumerate(summary.prices):
        left = layout.margin_x + index * slot_width + (slot_width - bar_width) / 2
        share = float(price.eur_per_mwh / tallest) if tallest > 0 else 0.0
        bar_height = max(0.0, share) * available_height * growth
        boxes.append((round(left), round(layout.baseline - bar_height), round(left + bar_width), layout.baseline))
    return boxes


def draw_price_chart(
    summary: DailyElectricitySummary,
    size: tuple[int, int] = VERTICAL_SIZE,
    progress: float = 1.0,
    theme: ChartTheme = DEFAULT_THEME,
) -> Image.Image:
    layout = _Layout(*size)
    image = Image.new("RGB", size, theme.background)
    draw = ImageDraw.Draw(image)
    _draw_header(draw, layout, summary, theme)
    boxes = bar_boxes(summary, size, progress)
    for price, box in zip(summary.prices, boxes):
        if box[1] < box[3]:
            draw.rectangle(box, fill=_bar_color(summary, price, theme))
    _draw_hour_axis(draw, layout, summary, boxes, theme)
    if progress >= 1.0:
        _draw_price_callout(draw, layout, summary.cheapest, boxes[summary.prices.index(summary.cheapest)], theme.cheapest, theme)
        _draw_price_callout(draw, layout, summary.most_expensive, boxes[summary.prices.index(summary.most_expensive)], theme.most_expensive, theme)
        _draw_legend(draw, layout, theme)
    return image


def render_price_chart_clip(
    summary: DailyElectricitySummary,
    output_path: str,
    duration: float = 6.0,
    fps: int = 30,
    size: tuple[int, int] = VERTICAL_SIZE,
    theme: ChartTheme = DEFAULT_THEME,
) -> str:
    growth_seconds = min(_MAX_GROWTH_SECONDS, duration * _GROWTH_SHARE_OF_DURATION)
    final_frame = np.array(draw_price_chart(summary, size, 1.0, theme))

    def frame_at(seconds: float) -> np.ndarray:
        if seconds >= growth_seconds:
            return final_frame
        return np.array(draw_price_chart(summary, size, seconds / growth_seconds, theme))

    clip = VideoClip(frame_function=frame_at, duration=duration)
    try:
        clip.write_videofile(output_path, fps=fps, codec="libx264", audio=False, logger=None)
    finally:
        clip.close()
    return output_path


def _ease_out(progress: float) -> float:
    clamped = min(1.0, max(0.0, progress))
    return 1 - (1 - clamped) ** 3


def _bar_color(summary: DailyElectricitySummary, price: HourlyPrice, theme: ChartTheme) -> Color:
    if price is summary.cheapest:
        return theme.cheapest
    if price is summary.most_expensive:
        return theme.most_expensive
    return theme.bar


def _font(layout: _Layout, share_of_width: float, theme: ChartTheme) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(utils.font_dir(), theme.font_file), layout.font_size(share_of_width))


def _draw_header(draw: ImageDraw.ImageDraw, layout: _Layout, summary: DailyElectricitySummary, theme: ChartTheme) -> None:
    center_x = layout.width / 2
    draw.text((center_x, layout.height * 0.13), TITLE, font=_font(layout, 0.085, theme), fill=theme.text, anchor="mm")
    draw.text((center_x, layout.height * 0.19), format_long_date(summary.day, SPANISH_SPAIN), font=_font(layout, 0.042, theme), fill=theme.muted, anchor="mm")


def _draw_hour_axis(
    draw: ImageDraw.ImageDraw,
    layout: _Layout,
    summary: DailyElectricitySummary,
    boxes: list[Box],
    theme: ChartTheme,
) -> None:
    font = _font(layout, 0.032, theme)
    label_y = layout.baseline + layout.height * 0.02
    for index in range(0, len(summary.prices), _HOUR_LABEL_STEP):
        left, _, right, _ = boxes[index]
        label = local_hour_label(summary.prices[index].starts_at)[:2]
        draw.text(((left + right) / 2, label_y), label, font=font, fill=theme.muted, anchor="mt")


def _draw_price_callout(
    draw: ImageDraw.ImageDraw,
    layout: _Layout,
    price: HourlyPrice,
    box: Box,
    color: Color,
    theme: ChartTheme,
) -> None:
    font = _font(layout, 0.04, theme)
    text = format_eur_per_kwh(price.eur_per_kwh)
    text_width = draw.textlength(text, font=font)
    center_x = (box[0] + box[2]) / 2
    half_width = text_width / 2
    center_x = min(max(center_x, layout.margin_x + half_width), layout.width - layout.margin_x - half_width)
    anchor_point = (center_x, box[1] - layout.height * 0.012)
    padding = layout.font_size(0.012)
    left, top, right, bottom = draw.textbbox(anchor_point, text, font=font, anchor="mb")
    draw.rounded_rectangle(
        (left - padding, top - padding, right + padding, bottom + padding),
        radius=padding,
        fill=theme.background,
    )
    draw.text(anchor_point, text, font=font, fill=color, anchor="mb")


def _draw_legend(draw: ImageDraw.ImageDraw, layout: _Layout, theme: ChartTheme) -> None:
    font = _font(layout, 0.036, theme)
    marker = layout.font_size(0.03)
    y = layout.height * 0.73
    x = layout.margin_x
    for label, color in ((CHEAPEST_LABEL, theme.cheapest), (MOST_EXPENSIVE_LABEL, theme.most_expensive)):
        draw.rectangle((x, y - marker / 2, x + marker, y + marker / 2), fill=color)
        x += marker * 1.6
        draw.text((x, y), label, font=font, fill=theme.text, anchor="lm")
        x += draw.textlength(label, font=font) + marker * 2
