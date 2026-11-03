from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from moviepy import VideoFileClip

from app.datavideo.charts import DEFAULT_THEME, bar_boxes, draw_price_chart, render_price_chart_clip
from app.datavideo.electricity import HourlyPrice, summarize_day

SIZE = (540, 960)


def summary_with_prices(eur_per_mwh_by_hour):
    midnight = datetime(2026, 11, 4, 0, 0, tzinfo=timezone(timedelta(hours=1)))
    prices = [
        HourlyPrice(starts_at=midnight + timedelta(hours=hour), eur_per_mwh=Decimal(price))
        for hour, price in enumerate(eur_per_mwh_by_hour)
    ]
    return summarize_day(date(2026, 11, 4), prices)


def sample_summary():
    prices = ["150"] * 24
    prices[14] = "82.4"
    prices[20] = "231.2"
    return summary_with_prices(prices)


def center(box):
    left, top, right, bottom = box
    return (left + right) // 2, (top + bottom) // 2


def test_cheapest_and_most_expensive_bars_use_highlight_colors():
    summary = sample_summary()

    image = draw_price_chart(summary, size=SIZE, progress=1.0)
    boxes = bar_boxes(summary, size=SIZE, progress=1.0)

    assert image.getpixel(center(boxes[14])) == DEFAULT_THEME.cheapest
    assert image.getpixel(center(boxes[20])) == DEFAULT_THEME.most_expensive
    assert image.getpixel(center(boxes[3])) == DEFAULT_THEME.bar


def test_bars_have_no_height_when_the_animation_starts():
    summary = sample_summary()

    image = draw_price_chart(summary, size=SIZE, progress=0.0)
    left, _, right, bottom = bar_boxes(summary, size=SIZE, progress=1.0)[20]

    assert image.getpixel(((left + right) // 2, bottom - 5)) == DEFAULT_THEME.background


def test_bar_heights_are_proportional_to_price():
    summary = sample_summary()

    heights = [bottom - top for _, top, _, bottom in bar_boxes(summary, size=SIZE, progress=1.0)]

    assert max(heights) == heights[20]
    assert abs(heights[14] / heights[20] - 82.4 / 231.2) < 0.02


def test_frame_has_the_requested_size():
    image = draw_price_chart(sample_summary(), size=SIZE, progress=0.5)

    assert image.size == SIZE


def test_clip_is_written_with_requested_size_and_duration(tmp_path):
    output = tmp_path / "chart.mp4"

    render_price_chart_clip(sample_summary(), str(output), duration=1.0, fps=10, size=(270, 480))

    with VideoFileClip(str(output)) as clip:
        assert tuple(clip.size) == (270, 480)
        assert abs(clip.duration - 1.0) < 0.2
