import pytest

from app.datavideo.narration import (
    NarrationRejected,
    build_narration_prompt,
    generate_verified_narration,
)

FACTS = [
    "Fecha: miércoles 4 de noviembre de 2026",
    "Hora más barata: de 14:00 a 15:00, a 0,082 €/kWh",
    "Hora más cara: de 20:00 a 21:00, a 0,231 €/kWh",
    "Precio medio del día: 0,146 €/kWh",
    "Franja de 3 horas más barata: de 13:00 a 16:00, a una media de 0,089 €/kWh",
    "Diferencia entre la hora más cara y la más barata: 181 %",
    "Fuente: Red Eléctrica, precio PVPC",
]

VALID_NARRATION = (
    "Mañana, miércoles 4 de noviembre, la luz más barata llega de 14:00 a 15:00, "
    "a 0,082 €/kWh. Si puedes, concentra el consumo en la franja de 13:00 a 16:00, "
    "con una media de 0,089 €/kWh. La hora más cara será de 20:00 a 21:00, "
    "a 0,231 €/kWh, y el precio medio del día se queda en 0,146 €/kWh. "
    "Entre la hora más cara y la más barata hay un 181 % de diferencia. "
    "Datos de Red Eléctrica, precio PVPC."
)

NARRATION_WITH_INVENTED_PRICE = VALID_NARRATION.replace("0,146", "0,150")


class ScriptedModel:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def test_prompt_places_every_fact_inside_the_data_block():
    prompt = build_narration_prompt(FACTS, topic="el precio de la luz de mañana")

    data_block = prompt.split("<facts>")[1].split("</facts>")[0]
    for fact in FACTS:
        assert f"- {fact}" in data_block


def test_first_draft_that_passes_is_returned_without_retrying():
    model = ScriptedModel(VALID_NARRATION)

    narration = generate_verified_narration(FACTS, topic="la luz", generate=model)

    assert narration == VALID_NARRATION
    assert len(model.prompts) == 1


def test_rejected_draft_is_retried_with_the_reason_in_the_next_prompt():
    model = ScriptedModel(NARRATION_WITH_INVENTED_PRICE, VALID_NARRATION)

    narration = generate_verified_narration(FACTS, topic="la luz", generate=model)

    assert narration == VALID_NARRATION
    assert "0,150" in model.prompts[1]


def test_provider_error_text_is_never_used_as_narration():
    model = ScriptedModel("Error: quota exceeded", VALID_NARRATION)

    narration = generate_verified_narration(FACTS, topic="la luz", generate=model)

    assert narration == VALID_NARRATION
    assert "quota exceeded" not in model.prompts[1]


def test_draft_outside_the_word_range_is_rejected():
    model = ScriptedModel("Mañana la luz más barata llega de 14:00 a 15:00.", VALID_NARRATION)

    narration = generate_verified_narration(FACTS, topic="la luz", generate=model)

    assert narration == VALID_NARRATION
    assert "words" in model.prompts[1]


def test_rejection_is_raised_when_every_attempt_fails():
    model = ScriptedModel(*[NARRATION_WITH_INVENTED_PRICE] * 3)

    with pytest.raises(NarrationRejected) as rejected:
        generate_verified_narration(FACTS, topic="la luz", generate=model, max_attempts=3)

    assert len(model.prompts) == 3
    assert any("0,150" in problem for problem in rejected.value.problems)


def test_surrounding_whitespace_is_trimmed():
    model = ScriptedModel(f"\n  {VALID_NARRATION}  \n")

    narration = generate_verified_narration(FACTS, topic="la luz", generate=model)

    assert narration == VALID_NARRATION
