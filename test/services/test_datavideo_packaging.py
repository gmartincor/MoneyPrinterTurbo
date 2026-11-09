from datetime import date

import pytest

from app.datavideo.facts import labelled_fact
from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.packaging import INSTAGRAM_CAPTION_LIMIT, build_package
from app.datavideo.script import Script, ScriptSegment
from app.datavideo.sources.ine import INE_SOURCE

AS_OF = date(2026, 9, 1)
SCRIPT = Script(
    title="Galicia y Castilla-La Mancha, a la cabeza de la inflación",
    segments=(
        ScriptSegment(text="En septiembre de 2026, la inflación anual fue del 4,9 %.", fact_keys=("national",), scene="big_number"),
        ScriptSegment(text="Fuente: INE.", fact_keys=(), scene="source_card"),
    ),
)
FACTS = [labelled_fact("national", "Inflación anual en España", "4,9 %", INE_SOURCE, AS_OF)]
TAGS = ("inflación", "IPC", "comunidades autónomas")


def package():
    return build_package(SCRIPT, FACTS, AS_OF, TAGS, SPANISH_SPAIN)


def test_title_and_tags_come_from_the_script_and_the_story():
    result = package()

    assert result.title == SCRIPT.title
    assert result.tags == TAGS


def test_description_tells_the_story_and_credits_the_source_with_its_attribution_and_month():
    description = package().description

    assert description.startswith(SCRIPT.segments[0].text)
    assert "Elaboración propia con datos extraídos del sitio web del INE: www.ine.es" in description
    assert "septiembre de 2026" in description


def test_description_discloses_the_ai_script_and_that_it_is_not_financial_advice():
    description = package().description

    assert "IA" in description
    assert "no es asesoramiento financiero" in description


def test_description_ends_with_hashtags_without_spaces():
    last_line = package().description.splitlines()[-1]

    assert last_line == "#inflación #IPC #comunidadesautónomas"


def test_description_fits_an_instagram_caption():
    assert len(package().description) <= INSTAGRAM_CAPTION_LIMIT


def test_a_description_too_long_for_instagram_is_rejected_instead_of_cut():
    long_script = Script(title="Título", segments=(ScriptSegment(text="palabra " * 400, fact_keys=(), scene="ranking"),))

    with pytest.raises(ValueError, match="limit"):
        build_package(long_script, FACTS, AS_OF, TAGS, SPANISH_SPAIN)
