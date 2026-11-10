import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.datavideo.sources.ine import Observation, Series, parse_table
from app.datavideo.stories.regional_ranking import (
    CPI_ANNUAL_BY_REGION,
    STORIES,
    build_ranking,
    describe_ranking,
    format_value,
)

FIXTURES = Path(__file__).parent / "fixtures" / "datavideo"
MEASURE = CPI_ANNUAL_BY_REGION.measure


def story_ranking(story):
    payload = json.loads((FIXTURES / f"ine_table_{story.table_id}.json").read_text(encoding="utf-8"))
    return build_ranking(parse_table(payload), story)


def fixture_ranking():
    return story_ranking(CPI_ANNUAL_BY_REGION)


def series(region, *observations):
    return Series(
        code=region,
        name=f"{region}. {MEASURE}",
        observations=tuple(Observation(year, period, Decimal(value)) for year, period, value in observations),
    )


def facts_by_key(ranking):
    return {fact.key: fact for fact in describe_ranking(ranking, CPI_ANNUAL_BY_REGION)}


def test_ranking_uses_the_latest_month_every_region_has_published():
    ranking = fixture_ranking()

    assert (ranking.year, ranking.period) == (2026, 9)
    assert ranking.national == Decimal("4.9")
    assert len(ranking.regions) == 19


def test_regions_are_sorted_from_highest_to_lowest_with_display_names():
    ranking = fixture_ranking()

    assert ranking.regions[0].value == Decimal("5.5")
    assert {item.region for item in ranking.highest} == {"Castilla-La Mancha", "Galicia"}
    assert [item.region for item in ranking.lowest] == ["Ceuta"]
    assert ranking.regions[-1].region == "Ceuta"


def test_other_measures_of_the_same_table_are_ignored():
    ranking = fixture_ranking()

    assert all(item.value < Decimal("6") for item in ranking.regions)


def test_previous_national_value_is_kept_when_the_previous_month_is_published():
    data = [
        series("Nacional", (2026, 9, "4.9"), (2026, 8, "4.5")),
        series("Galicia", (2026, 9, "5.5"), (2026, 8, "5.0")),
        series("Ceuta", (2026, 9, "3.1"), (2026, 8, "3.0")),
    ]

    ranking = build_ranking(data, CPI_ANNUAL_BY_REGION)

    assert ranking.previous_national == Decimal("4.5")


def test_ranking_without_a_month_shared_by_every_region_is_rejected():
    data = [
        series("Nacional", (2026, 9, "4.9")),
        series("Galicia", (2026, 9, "5.5")),
        series("Ceuta", (2026, 8, "3.0")),
    ]

    with pytest.raises(ValueError, match="period"):
        build_ranking(data, CPI_ANNUAL_BY_REGION)


def test_facts_state_the_month_the_national_figure_and_both_extremes():
    facts = facts_by_key(fixture_ranking())

    assert facts["period"].statement == "Mes del dato: septiembre de 2026"
    assert facts["national"].statement == "Inflación anual en España: 4,9 %"
    assert facts["highest"].statement == "Inflación anual más alta: Castilla-La Mancha y Galicia, 5,5 %"
    assert facts["lowest"].statement == "Inflación anual más baja: Ceuta (ciudad autónoma), 3,1 %"


def test_facts_include_the_gap_and_how_many_regions_are_above_the_national_figure():
    facts = facts_by_key(fixture_ranking())

    assert facts["gap"].statement == "Diferencia entre la inflación anual más alta y la más baja: 2,4 puntos"
    assert facts["above_national"].statement == (
        "Comunidades y ciudades autónomas por encima del dato nacional: 10 de 19"
    )


def test_every_region_has_its_own_fact():
    facts = facts_by_key(fixture_ranking())

    assert facts["region_comunidad_de_madrid"].statement == "Comunidad de Madrid: 5,3 %"
    assert facts["region_castilla_la_mancha"].statement == "Castilla-La Mancha: 5,5 %"


def test_facts_carry_the_ine_source_and_the_month_they_describe():
    fact = facts_by_key(fixture_ranking())["national"]

    assert fact.source.name == "INE"
    assert fact.as_of == date(2026, 9, 1)
    assert fact.label == "Inflación anual en España"
    assert fact.value == "4,9 %"


def test_story_key_identifies_the_measure_and_the_month():
    assert fixture_ranking().story_key == "ipc_anual_ccaa_2026_09"


@pytest.mark.parametrize("key", sorted(STORIES))
def test_every_story_finds_its_national_and_regional_series_in_real_ine_data(key):
    ranking = story_ranking(STORIES[key])
    facts = describe_ranking(ranking, STORIES[key])

    assert len(ranking.regions) >= 17
    assert len({fact.key for fact in facts}) == len(facts)


def test_a_quarterly_story_reads_ine_quarters_and_names_the_quarter():
    story = STORIES["paro_ccaa"]
    ranking = story_ranking(story)
    facts = {fact.key: fact for fact in describe_ranking(ranking, story)}

    assert (ranking.year, ranking.period) == (2026, 3)
    assert ranking.story_key == "paro_ccaa_2026_t3"
    assert ranking.as_of == date(2026, 7, 1)
    assert ranking.period_label("es-ES") == "tercer trimestre de 2026"
    assert facts["period"].statement == "Trimestre del dato: tercer trimestre de 2026"
    assert facts["national"].statement == "Tasa de paro en España: 10,18 %"
    assert facts["previous_national"].statement == "Tasa de paro en España, segundo trimestre de 2026: 9,87 %"


def test_the_quarter_before_the_first_one_is_the_last_quarter_of_the_previous_year():
    story = STORIES["paro_ccaa"]
    name = "Tasa de paro de la población. Ambos sexos. {region}. Total."
    data = [
        Series(code=region, name=name.format(region=region), observations=(
            Observation(2026, 19, Decimal("10")), Observation(2025, 22, Decimal("9"))
        ))
        for region in ("Total Nacional", "Galicia", "Ceuta")
    ]

    ranking = build_ranking(data, story)

    assert ranking.story_key == "paro_ccaa_2026_t1"
    assert ranking.previous_national == Decimal("9")


def test_a_story_in_euros_ranks_whole_euros_and_measures_the_gap_in_euros():
    story = STORIES["salario_ccaa"]
    ranking = story_ranking(story)
    facts = {fact.key: fact for fact in describe_ranking(ranking, story)}

    assert ranking.highest[0].region == "Comunidad de Madrid"
    assert facts["highest"].statement == "Coste salarial por trabajador y mes más alto: Comunidad de Madrid, 3061 €"
    assert facts["lowest"].statement == "Coste salarial por trabajador y mes más bajo: Canarias, 2016 €"
    assert facts["gap"].statement == (
        "Diferencia entre el coste salarial por trabajador y mes más alto y el más bajo: 1044 €"
    )
    assert facts["above_national"].statement == "Comunidades autónomas por encima del dato nacional: 4 de 17"


def test_values_are_written_in_the_unit_and_precision_of_their_story():
    assert format_value(CPI_ANNUAL_BY_REGION, Decimal("4.94"), "es-ES") == "4,9 %"
    assert format_value(STORIES["paro_ccaa"], Decimal("10.18"), "es-ES") == "10,18 %"
    assert format_value(STORIES["salario_ccaa"], Decimal("2512.68"), "es-ES") == "2513 €"
