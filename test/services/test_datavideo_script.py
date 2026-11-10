import json
from datetime import date

import pytest

from app.datavideo.facts import Fact, Source
from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.script import (
    ScriptRejected,
    build_script_prompt,
    generate_verified_script,
    script_from_dict,
    script_to_dict,
)

SOURCE = Source(name="Red Eléctrica, precio PVPC", url="https://example.org", license="test")
DAY = date(2026, 11, 4)


def fact(key, statement):
    return Fact(key=key, statement=statement, source=SOURCE, as_of=DAY)


FACTS = [
    fact("date", "Fecha: miércoles 4 de noviembre de 2026"),
    fact("cheapest_hour", "Hora más barata: de 14:00 a 15:00, a 0,082 €/kWh"),
    fact("most_expensive_hour", "Hora más cara: de 20:00 a 21:00, a 0,231 €/kWh"),
    fact("daily_average", "Precio medio del día: 0,146 €/kWh"),
    fact("cheapest_window", "Franja de 3 horas más barata: de 13:00 a 16:00, a una media de 0,089 €/kWh"),
    fact("price_gap", "Diferencia entre la hora más cara y la más barata: 181 %"),
]
SCENES = {
    "hourly_prices": "Animated bar chart of every hourly price, cheapest and most expensive highlighted",
    "big_number": "One figure shown very large",
}


def segment(text, facts, scene="hourly_prices"):
    return {"text": text, "facts": facts, "scene": scene}


VALID_SEGMENTS = [
    segment("¿Luz barata mañana? De 14:00 a 15:00, solo 0,082 €/kWh.", ["cheapest_hour"]),
    segment("Es el precio del miércoles 4 de noviembre de 2026, según Red Eléctrica.", ["date"]),
    segment("La mejor franja dura 3 horas: de 13:00 a 16:00, a 0,089 €/kWh.", ["cheapest_window"]),
    segment("Y la hora más cara llega de 20:00 a 21:00.", ["most_expensive_hour"]),
    segment("Ahí pagarás 0,231 €/kWh, frente a una media diaria de 0,146 €/kWh.",
            ["most_expensive_hour", "daily_average"]),
    segment("Entre la hora más cara y la más barata hay un 181 % de diferencia.", ["price_gap"],
            scene="big_number"),
    segment("¿Vas a cambiar tu horario? Sigue el canal para el precio de cada día.", []),
]


def reply(title="La luz más barata de mañana", segments=None):
    return json.dumps({"title": title, "segments": segments if segments is not None else VALID_SEGMENTS},
                      ensure_ascii=False)


class ScriptedModel:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def generate(model, **overrides):
    arguments = {
        "facts": FACTS,
        "topic": "el precio de la luz de mañana",
        "locale": SPANISH_SPAIN,
        "scenes": SCENES,
        "generate": model,
    }
    arguments.update(overrides)
    return generate_verified_script(**arguments)


def test_prompt_lists_every_fact_with_its_key_inside_the_data_block():
    prompt = build_script_prompt(FACTS, "la luz", SPANISH_SPAIN, SCENES)

    data_block = prompt.split("<facts>")[1].split("</facts>")[0]
    for item in FACTS:
        assert f"[{item.key}] {item.statement}" in data_block


def test_prompt_offers_only_the_available_scenes_and_names_the_source():
    prompt = build_script_prompt(FACTS, "la luz", SPANISH_SPAIN, SCENES)

    assert "hourly_prices" in prompt
    assert "big_number" in prompt
    assert "Red Eléctrica, precio PVPC" in prompt


def test_valid_reply_becomes_a_script_with_segments_in_order():
    script = generate(ScriptedModel(reply()))

    assert script.title == "La luz más barata de mañana"
    assert [item.scene for item in script.segments] == ["hourly_prices"] * 5 + ["big_number", "hourly_prices"]
    assert script.segments[0].fact_keys == ("cheapest_hour",)
    assert script.narration.startswith("¿Luz barata mañana?")


def test_reply_wrapped_in_a_code_fence_is_accepted():
    script = generate(ScriptedModel(f"```json\n{reply()}\n```"))

    assert len(script.segments) == 7


def test_reply_that_is_not_json_is_retried_with_the_reason():
    model = ScriptedModel("Aquí tienes el guion: ...", reply())

    script = generate(model)

    assert len(script.segments) == 7
    assert "JSON" in model.prompts[1]


def test_segment_figures_must_come_from_the_facts_that_segment_references():
    segments = list(VALID_SEGMENTS)
    segments[0] = segment("La luz más barata llega de 14:00 a 15:00, a 0,231 €/kWh.", ["cheapest_hour"])
    model = ScriptedModel(reply(segments=segments), reply())

    generate(model)

    assert "0,231" in model.prompts[1]


def test_unknown_fact_keys_are_rejected():
    segments = list(VALID_SEGMENTS)
    segments[5] = segment("Entre la hora más cara y la más barata hay un 181 % de diferencia.", ["gap"])
    model = ScriptedModel(reply(segments=segments), reply())

    generate(model)

    assert "gap" in model.prompts[1]


def test_unknown_scenes_are_rejected():
    segments = list(VALID_SEGMENTS)
    segments[6] = segment("¿Vas a cambiar tu horario? Sigue el canal.", [], scene="stock_footage")
    model = ScriptedModel(reply(segments=segments), reply())

    generate(model)

    assert "stock_footage" in model.prompts[1]


def test_title_cannot_contain_figures_missing_from_the_facts():
    model = ScriptedModel(reply(title="La luz baja un 40 % mañana"), reply())

    generate(model)

    assert "40" in model.prompts[1]


def test_provider_error_text_is_never_copied_into_the_next_prompt():
    model = ScriptedModel("Error: quota exceeded", reply())

    script = generate(model)

    assert len(script.segments) == 7
    assert "quota exceeded" not in model.prompts[1]


def test_narration_outside_the_word_range_is_rejected():
    short_segments = [segment("Mañana la luz más barata llega de 14:00 a 15:00.", ["cheapest_hour"])]
    model = ScriptedModel(reply(segments=short_segments), reply())

    generate(model)

    assert "words" in model.prompts[1]


def test_rejection_lists_the_problems_when_every_attempt_fails():
    model = ScriptedModel(*[reply(title="Baja un 40 %")] * 3)

    with pytest.raises(ScriptRejected) as rejected:
        generate(model, max_attempts=3)

    assert len(model.prompts) == 3
    assert any("40" in problem for problem in rejected.value.problems)


def test_scenes_that_show_a_fact_must_reference_one():
    segments = list(VALID_SEGMENTS)
    segments[6] = segment("¿Vas a cambiar tu horario? Sigue el canal.", [], scene="big_number")
    model = ScriptedModel(reply(segments=segments), reply())

    generate(model, fact_scenes=frozenset({"big_number"}))

    assert "segment 7" in model.prompts[1]
    assert "big_number" in model.prompts[1]


def test_a_saved_script_is_restored_exactly():
    script = generate(ScriptedModel(reply()))

    assert script_from_dict(json.loads(json.dumps(script_to_dict(script)))) == script


def test_a_saved_script_with_a_broken_shape_is_rejected():
    with pytest.raises(ValueError, match="script"):
        script_from_dict({"title": "Sin segmentos"})


def test_a_segment_too_long_to_keep_the_picture_moving_is_rejected():
    segments = list(VALID_SEGMENTS)
    segments[2] = segment(
        "La mejor franja dura 3 horas, de 13:00 a 16:00, con una media de 0,089 €/kWh en toda la franja.",
        ["cheapest_window"],
    )
    model = ScriptedModel(reply(segments=segments), reply())

    generate(model)

    assert "segment 3" in model.prompts[1]
    assert "16 words" in model.prompts[1]


def test_too_few_segments_to_change_the_picture_are_rejected():
    long_segments = VALID_SEGMENTS[:5]
    model = ScriptedModel(reply(segments=long_segments), reply())

    generate(model)

    assert "segments" in model.prompts[1]


def test_a_hook_longer_than_a_quick_line_is_rejected():
    segments = list(VALID_SEGMENTS)
    segments[0] = segment("¿Sabes cuándo será mañana la luz más barata? De 14:00 a 15:00, 0,082 €/kWh.", ["cheapest_hour"])
    model = ScriptedModel(reply(segments=segments), reply())

    generate(model)

    assert "hook" in model.prompts[1]


@pytest.mark.parametrize(
    "closing",
    ["Contenido generado con inteligencia artificial.", "Guion hecho con IA a partir de datos oficiales."],
)
def test_the_narration_never_talks_about_artificial_intelligence(closing):
    segments = list(VALID_SEGMENTS)
    segments[6] = segment(closing, [])
    model = ScriptedModel(reply(segments=segments), reply())

    generate(model)

    assert "artificial intelligence" in model.prompts[1]


def test_the_prompt_asks_for_a_hook_a_presenter_voice_and_a_closing_line():
    prompt = build_script_prompt(FACTS, "la luz", SPANISH_SPAIN, SCENES)

    assert "hook" in prompt
    assert "viewer" in prompt
    assert "Never mention artificial intelligence" in prompt
