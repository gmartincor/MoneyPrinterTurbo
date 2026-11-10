from datetime import date
from decimal import Decimal

import pytest

from app.datavideo.facts import labelled_fact
from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.scenes.base import HORIZONTAL_SIZE, VERTICAL_SIZE, content_box
from app.datavideo.scenes.catalog import (
    FACT_SCENES,
    SCENE_DESCRIPTIONS,
    SceneContext,
    build_scene,
    credit_line,
)
from app.datavideo.scenes.base import CreditedScene
from app.datavideo.scenes.figures import BigNumberScene, counting_value
from app.datavideo.scenes.ranking import RankingScene
from app.datavideo.sources.ine import INE_SOURCE
from app.datavideo.scenes import ranking as ranking_module
from app.datavideo.stories.regional_ranking import (
    CPI_ANNUAL_BY_REGION,
    STORIES,
    RegionalRanking,
    RegionalValue,
    describe_ranking,
)
from app.datavideo.theme import DEFAULT_THEME, Theme

SMALL_VERTICAL = (540, 960)
SMALL_HORIZONTAL = (960, 540)


def ranking(*values, national="4.9", story=CPI_ANNUAL_BY_REGION, period=9):
    regions = tuple(RegionalValue(region=f"Región {index}", value=Decimal(value)) for index, value in enumerate(values))
    ordered = tuple(sorted(regions, key=lambda item: -item.value))
    return RegionalRanking(
        story=story, year=2026, period=period, national=Decimal(national), previous_national=None,
        regions=ordered,
    )


def ranking_scene(theme=DEFAULT_THEME, *values):
    values = values or ("5.5", "5.0", "4.4", "3.1")
    return RankingScene(ranking=ranking(*values), theme=theme, locale=SPANISH_SPAIN)


def center(box):
    left, top, right, bottom = box
    return (left + right) // 2, (top + bottom) // 2


@pytest.mark.parametrize("size", [SMALL_VERTICAL, SMALL_HORIZONTAL])
def test_highest_and_lowest_bars_use_the_warning_and_good_colors(size):
    scene = ranking_scene()

    image = scene.draw(size, progress=1.0)
    boxes = scene.bar_boxes(size, progress=1.0)

    assert image.getpixel(center(boxes[0])) == DEFAULT_THEME.negative
    assert image.getpixel(center(boxes[-1])) == DEFAULT_THEME.positive
    assert image.getpixel(center(boxes[1])) == DEFAULT_THEME.neutral


def test_bars_are_proportional_to_their_values():
    scene = ranking_scene()

    widths = [right - left for left, _, right, _ in scene.bar_boxes(SMALL_VERTICAL, progress=1.0)]

    assert widths[0] == max(widths)
    assert abs(widths[-1] / widths[0] - 3.1 / 5.5) < 0.02


def test_bars_have_no_length_when_the_animation_starts():
    scene = ranking_scene()

    assert all(right - left <= 1 for left, _, right, _ in scene.bar_boxes(SMALL_VERTICAL, progress=0.0))


def test_negative_values_grow_to_the_left_of_zero():
    scene = ranking_scene(DEFAULT_THEME, "1.2", "-0.4")

    positive, negative = scene.bar_boxes(SMALL_VERTICAL, progress=1.0)

    assert negative[2] <= positive[0] + 1


def test_bars_stay_inside_the_content_area_above_the_subtitles():
    scene = ranking_scene()
    _, top, _, bottom = content_box(VERTICAL_SIZE)

    for _, box_top, _, box_bottom in scene.bar_boxes(VERTICAL_SIZE, progress=1.0):
        assert top <= box_top and box_bottom <= bottom


def test_the_national_line_never_crosses_a_value_label():
    scene = ranking_scene(DEFAULT_THEME, "5.5", "4.95", "4.9", "4.85", "3.1")

    image = scene.draw(SMALL_VERTICAL, progress=1.0)

    for index in range(5):
        left, top, right, bottom = scene.value_label_box(SMALL_VERTICAL, index)
        label_colors = {color for _, color in image.crop((left, top, right, bottom)).getcolors(maxcolors=100000)}
        assert DEFAULT_THEME.muted not in label_colors


def test_scene_colors_come_from_the_theme():
    theme = Theme(background=(255, 255, 255), negative=(0, 0, 255))
    scene = ranking_scene(theme)

    image = scene.draw(SMALL_VERTICAL, progress=1.0)

    assert image.getpixel(center(scene.bar_boxes(SMALL_VERTICAL, progress=1.0)[0])) == (0, 0, 255)
    assert image.getpixel((2, 2)) == (255, 255, 255)


@pytest.mark.parametrize("size", [VERTICAL_SIZE, HORIZONTAL_SIZE])
def test_every_scene_draws_frames_of_the_requested_size(size):
    fact = labelled_fact("national", "Inflación anual en España", "4,9 %", INE_SOURCE, date(2026, 9, 1))
    scenes = [
        ranking_scene(),
        BigNumberScene(fact=fact, color=DEFAULT_THEME.text, theme=DEFAULT_THEME),
    ]

    for scene in scenes:
        assert scene.draw(size, progress=0.5).size == size


def test_big_number_fades_in_from_the_background():
    fact = labelled_fact("national", "Inflación anual en España", "4,9 %", INE_SOURCE, date(2026, 9, 1))
    scene = BigNumberScene(fact=fact, color=DEFAULT_THEME.negative, theme=DEFAULT_THEME)

    start_colors = {color for _, color in scene.draw(SMALL_VERTICAL, progress=0.0).getcolors(maxcolors=100000)}
    end_colors = {color for _, color in scene.draw(SMALL_VERTICAL, progress=1.0).getcolors(maxcolors=100000)}

    assert DEFAULT_THEME.negative not in start_colors
    assert DEFAULT_THEME.negative in end_colors


def context():
    data = ranking("5.5", "5.0", "4.4", "3.1")
    return SceneContext(
        ranking=data,
        facts={fact.key: fact for fact in describe_ranking(data, CPI_ANNUAL_BY_REGION)},
        theme=DEFAULT_THEME,
        locale=SPANISH_SPAIN,
    )


def test_catalog_describes_every_scene_it_can_build():
    assert set(SCENE_DESCRIPTIONS) == {"ranking", "big_number"}
    assert FACT_SCENES == frozenset({"big_number"})


def test_big_number_shows_the_first_fact_the_segment_references_in_its_story_color():
    scene = build_scene("big_number", ("highest", "national"), context())

    assert isinstance(scene, BigNumberScene)
    assert scene.fact.key == "highest"
    assert scene.color == DEFAULT_THEME.negative


def test_lowest_value_is_shown_in_the_good_color_when_lower_is_better():
    scene = build_scene("big_number", ("lowest",), context())

    assert scene.color == DEFAULT_THEME.positive


def test_the_ranking_is_built_from_the_story():
    assert isinstance(build_scene("ranking", (), context()), RankingScene)


@pytest.mark.parametrize(
    "locale, expected", [(SPANISH_SPAIN, "Fuente: INE · septiembre de 2026"), ("en-US", "Source: INE · September 2026")]
)
def test_the_credit_names_the_source_and_the_period(locale, expected):
    period = "septiembre de 2026" if locale == SPANISH_SPAIN else "September 2026"

    assert credit_line(INE_SOURCE, period, locale) == expected


@pytest.mark.parametrize("size", [SMALL_VERTICAL, SMALL_HORIZONTAL])
def test_a_credited_scene_shows_the_credit_just_below_the_picture(size):
    fact = labelled_fact("national", "Inflación anual en España", "4,9 %", INE_SOURCE, date(2026, 9, 1))
    plain = BigNumberScene(fact=fact, color=DEFAULT_THEME.text, theme=DEFAULT_THEME)
    bottom = content_box(size)[3]
    band = (0, bottom, size[0], bottom + round(min(size) * 0.06))

    credited = CreditedScene(scene=plain, credit="Fuente: INE · septiembre de 2026", theme=DEFAULT_THEME).draw(size, 1.0)

    assert credited.crop(band).getcolors(10_000) != plain.draw(size, 1.0).crop(band).getcolors(10_000)
    assert credited.crop((0, 0, size[0], bottom)).tobytes() == plain.draw(size, 1.0).crop((0, 0, size[0], bottom)).tobytes()


def test_unknown_scenes_and_big_numbers_without_facts_are_rejected():
    with pytest.raises(ValueError, match="scene"):
        build_scene("stock_footage", (), context())
    with pytest.raises(ValueError, match="fact"):
        build_scene("big_number", (), context())


@pytest.mark.parametrize("size", [SMALL_VERTICAL, SMALL_HORIZONTAL])
def test_euro_value_labels_fit_inside_the_frame(size):
    wages = ranking("3060.53", "2770.19", "2016.13", national="2512.68", story=STORIES["salario_ccaa"], period=2)
    scene = RankingScene(ranking=wages, theme=DEFAULT_THEME, locale=SPANISH_SPAIN)

    assert all(scene.value_label_box(size, index)[2] <= size[0] for index in range(3))


def test_the_ranking_header_names_the_quarter_of_a_quarterly_story(monkeypatch):
    headers = []
    monkeypatch.setattr(ranking_module, "draw_header", lambda draw, size, theme, title, subtitle: headers.append(subtitle))
    unemployment = ranking("18.87", "4.63", national="10.18", story=STORIES["paro_ccaa"], period=3)

    RankingScene(ranking=unemployment, theme=DEFAULT_THEME, locale=SPANISH_SPAIN).draw(SMALL_VERTICAL, 1.0)

    assert headers == ["tercer trimestre de 2026"]


@pytest.mark.parametrize(
    "value, amount, expected",
    [("18,87 %", 0.0, "0,00 %"), ("18,87 %", 1.0, "18,87 %"), ("10 de 19", 0.0, "0 de 19"), ("2513 €", 0.5, "1256 €")],
)
def test_big_numbers_count_up_to_their_exact_value(value, amount, expected):
    assert counting_value(value, amount) == expected


def test_a_ranking_scene_focuses_on_the_regions_the_segment_talks_about():
    scene = build_scene("ranking", ("highest",), context())

    assert scene.focus == frozenset(item.region for item in scene.ranking.highest)


def test_a_region_fact_focuses_on_that_region():
    scene = build_scene("ranking", ("region_region_3",), context())

    assert scene.focus == frozenset({"Región 3"})


@pytest.mark.parametrize("size", [SMALL_VERTICAL, SMALL_HORIZONTAL])
def test_bars_outside_the_focus_are_dimmed(size):
    focused = RankingScene(
        ranking=ranking("5.5", "5.0", "4.4", "3.1"), theme=DEFAULT_THEME, locale=SPANISH_SPAIN, focus=frozenset({"Región 0"})
    )

    image = focused.draw(size, progress=1.0)
    boxes = focused.bar_boxes(size, progress=1.0)

    assert image.getpixel(center(boxes[0])) == DEFAULT_THEME.negative
    assert image.getpixel(center(boxes[1])) != DEFAULT_THEME.neutral


def test_the_period_is_never_animated_as_a_count():
    scene = build_scene("big_number", ("period",), context())

    assert scene.counting is False
    assert build_scene("big_number", ("national",), context()).counting is True
