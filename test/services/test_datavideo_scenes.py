from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from moviepy import VideoFileClip

from app.datavideo.electricity import HourlyPrice, summarize_day
from app.datavideo.scenes.base import HORIZONTAL_SIZE, VERTICAL_SIZE, render_scene_clip
from app.datavideo.scenes.hourly_prices import HourlyPricesScene
from app.datavideo.theme import DEFAULT_THEME, Theme

SMALL_VERTICAL = (540, 960)
SMALL_HORIZONTAL = (960, 540)


def summary_with_prices(eur_per_mwh_by_hour):
    midnight = datetime(2026, 11, 4, 0, 0, tzinfo=timezone(timedelta(hours=1)))
    prices = [
        HourlyPrice(starts_at=midnight + timedelta(hours=hour), eur_per_mwh=Decimal(price))
        for hour, price in enumerate(eur_per_mwh_by_hour)
    ]
    return summarize_day(date(2026, 11, 4), prices)


def sample_scene(theme=DEFAULT_THEME):
    prices = ["150"] * 24
    prices[14] = "82.4"
    prices[20] = "231.2"
    return HourlyPricesScene(summary=summary_with_prices(prices), theme=theme)


def center(box):
    left, top, right, bottom = box
    return (left + right) // 2, (top + bottom) // 2


@pytest.mark.parametrize("size", [SMALL_VERTICAL, SMALL_HORIZONTAL])
def test_cheapest_and_most_expensive_bars_use_the_theme_highlight_colors(size):
    scene = sample_scene()

    image = scene.draw(size, progress=1.0)
    boxes = scene.bar_boxes(size, progress=1.0)

    assert image.getpixel(center(boxes[14])) == DEFAULT_THEME.positive
    assert image.getpixel(center(boxes[20])) == DEFAULT_THEME.negative
    assert image.getpixel(center(boxes[3])) == DEFAULT_THEME.neutral


def test_colors_come_from_the_theme_it_is_given():
    theme = Theme(background=(255, 255, 255), neutral=(10, 10, 10), positive=(0, 0, 255), negative=(255, 0, 255))
    scene = sample_scene(theme)

    image = scene.draw(SMALL_VERTICAL, progress=1.0)
    boxes = scene.bar_boxes(SMALL_VERTICAL, progress=1.0)

    assert image.getpixel(center(boxes[14])) == (0, 0, 255)
    assert image.getpixel((2, 2)) == (255, 255, 255)


def test_bars_have_no_height_when_the_animation_starts():
    scene = sample_scene()

    image = scene.draw(SMALL_VERTICAL, progress=0.0)
    left, _, right, bottom = scene.bar_boxes(SMALL_VERTICAL, progress=1.0)[20]

    assert image.getpixel(((left + right) // 2, bottom - 5)) == DEFAULT_THEME.background


def test_bar_heights_are_proportional_to_price():
    heights = [bottom - top for _, top, _, bottom in sample_scene().bar_boxes(SMALL_VERTICAL, progress=1.0)]

    assert max(heights) == heights[20]
    assert abs(heights[14] / heights[20] - 82.4 / 231.2) < 0.02


@pytest.mark.parametrize("size", [VERTICAL_SIZE, HORIZONTAL_SIZE])
def test_frames_have_the_requested_size(size):
    assert sample_scene().draw(size, progress=0.5).size == size


def test_clip_is_written_with_requested_size_and_duration(tmp_path):
    output = tmp_path / "scene.mp4"

    render_scene_clip(sample_scene(), str(output), duration=1.0, fps=10, size=(270, 480))

    with VideoFileClip(str(output)) as clip:
        assert tuple(clip.size) == (270, 480)
        assert abs(clip.duration - 1.0) < 0.2
