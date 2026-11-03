from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from app.datavideo.electricity import DailyElectricitySummary, HourlyPrice, format_eur_per_kwh, local_hour_label
from app.datavideo.locale import SPANISH_SPAIN, format_long_date
from app.datavideo.scenes.base import Box, Size, ease_out, load_font
from app.datavideo.theme import Color, Theme

SCENE_ID = "hourly_prices"
DESCRIPTION = (
    "Animated bar chart of every hourly electricity price of the day, "
    "cheapest hour in green and most expensive hour in red, each with its price"
)
TITLE = "Precio de la luz"
CHEAPEST_LABEL = "Más barata"
MOST_EXPENSIVE_LABEL = "Más cara"
_HOUR_LABEL_STEP = 6
_TITLE_FONT_SHARE = 0.085
_HOUR_FONT_SHARE = 0.032


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

    @property
    def title_y(self) -> float:
        return self.height * 0.13

    @property
    def date_y(self) -> float:
        return self.title_y + self.font_size(_TITLE_FONT_SHARE) * 1.1

    @property
    def hour_label_y(self) -> float:
        return self.baseline + self.font_size(0.02)

    @property
    def legend_y(self) -> float:
        return self.hour_label_y + self.font_size(_HOUR_FONT_SHARE) + self.font_size(0.05)

    def font_size(self, share_of_short_side: float) -> int:
        return round(min(self.width, self.height) * share_of_short_side)


@dataclass(frozen=True)
class HourlyPricesScene:
    summary: DailyElectricitySummary
    theme: Theme

    def bar_boxes(self, size: Size, progress: float) -> list[Box]:
        layout = _Layout(*size)
        prices = self.summary.prices
        slot_width = (layout.width - 2 * layout.margin_x) / len(prices)
        bar_width = slot_width * 0.7
        tallest = max(price.eur_per_mwh for price in prices)
        available_height = layout.baseline - layout.chart_top
        growth = ease_out(progress)
        boxes = []
        for index, price in enumerate(prices):
            left = layout.margin_x + index * slot_width + (slot_width - bar_width) / 2
            share = float(price.eur_per_mwh / tallest) if tallest > 0 else 0.0
            bar_height = max(0.0, share) * available_height * growth
            boxes.append((round(left), round(layout.baseline - bar_height), round(left + bar_width), layout.baseline))
        return boxes

    def draw(self, size: Size, progress: float) -> Image.Image:
        layout = _Layout(*size)
        image = Image.new("RGB", size, self.theme.background)
        draw = ImageDraw.Draw(image)
        self._draw_header(draw, layout)
        boxes = self.bar_boxes(size, progress)
        for price, box in zip(self.summary.prices, boxes):
            if box[1] < box[3]:
                draw.rectangle(box, fill=self._bar_color(price))
        self._draw_hour_axis(draw, layout, boxes)
        if progress >= 1.0:
            cheapest, most_expensive = self.summary.cheapest, self.summary.most_expensive
            self._draw_price_callout(draw, layout, cheapest, boxes[self.summary.prices.index(cheapest)], self.theme.positive)
            self._draw_price_callout(
                draw, layout, most_expensive, boxes[self.summary.prices.index(most_expensive)], self.theme.negative
            )
            self._draw_legend(draw, layout)
        return image

    def _font(self, layout: _Layout, share_of_short_side: float) -> ImageFont.FreeTypeFont:
        return load_font(self.theme, layout.font_size(share_of_short_side))

    def _bar_color(self, price: HourlyPrice) -> Color:
        if price is self.summary.cheapest:
            return self.theme.positive
        if price is self.summary.most_expensive:
            return self.theme.negative
        return self.theme.neutral

    def _draw_header(self, draw: ImageDraw.ImageDraw, layout: _Layout) -> None:
        center_x = layout.width / 2
        draw.text(
            (center_x, layout.title_y), TITLE, font=self._font(layout, _TITLE_FONT_SHARE), fill=self.theme.text, anchor="mm"
        )
        draw.text(
            (center_x, layout.date_y),
            format_long_date(self.summary.day, SPANISH_SPAIN),
            font=self._font(layout, 0.042),
            fill=self.theme.muted,
            anchor="mm",
        )

    def _draw_hour_axis(self, draw: ImageDraw.ImageDraw, layout: _Layout, boxes: list[Box]) -> None:
        font = self._font(layout, _HOUR_FONT_SHARE)
        for index in range(0, len(self.summary.prices), _HOUR_LABEL_STEP):
            left, _, right, _ = boxes[index]
            label = local_hour_label(self.summary.prices[index].starts_at)[:2]
            draw.text(((left + right) / 2, layout.hour_label_y), label, font=font, fill=self.theme.muted, anchor="mt")

    def _draw_price_callout(
        self, draw: ImageDraw.ImageDraw, layout: _Layout, price: HourlyPrice, box: Box, color: Color
    ) -> None:
        font = self._font(layout, 0.04)
        text = format_eur_per_kwh(price.eur_per_kwh)
        half_width = draw.textlength(text, font=font) / 2
        center_x = (box[0] + box[2]) / 2
        center_x = min(max(center_x, layout.margin_x + half_width), layout.width - layout.margin_x - half_width)
        anchor_point = (center_x, box[1] - layout.height * 0.012)
        padding = layout.font_size(0.012)
        left, top, right, bottom = draw.textbbox(anchor_point, text, font=font, anchor="mb")
        draw.rounded_rectangle(
            (left - padding, top - padding, right + padding, bottom + padding),
            radius=padding,
            fill=self.theme.background,
        )
        draw.text(anchor_point, text, font=font, fill=color, anchor="mb")

    def _draw_legend(self, draw: ImageDraw.ImageDraw, layout: _Layout) -> None:
        font = self._font(layout, 0.036)
        marker = layout.font_size(0.03)
        y = layout.legend_y
        x = layout.margin_x
        for label, color in ((CHEAPEST_LABEL, self.theme.positive), (MOST_EXPENSIVE_LABEL, self.theme.negative)):
            draw.rectangle((x, y - marker / 2, x + marker, y + marker / 2), fill=color)
            x += marker * 1.6
            draw.text((x, y), label, font=font, fill=self.theme.text, anchor="lm")
            x += draw.textlength(label, font=font) + marker * 2
