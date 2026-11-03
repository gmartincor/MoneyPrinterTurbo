from app.datavideo.figures import verify_figures

FACTS = [
    "Fecha: miércoles 4 de noviembre de 2026",
    "Hora más barata: de 14:00 a 15:00, a 0,082 €/kWh",
    "Hora más cara: de 20:00 a 21:00, a 0,231 €/kWh",
    "Precio medio del día: 0,148 €/kWh",
    "Diferencia entre la hora más cara y la más barata: 182 %",
]


def test_narration_using_only_fact_figures_passes():
    narration = (
        "Mañana, miércoles 4 de noviembre, la luz más barata será de 14:00 a 15:00, "
        "a 0,082 €/kWh. La más cara, de 20:00 a 21:00, a 0,231 €/kWh. "
        "De media pagarás 0,148 €/kWh, y la hora cara cuesta un 182 % más."
    )

    check = verify_figures(narration, FACTS)

    assert check.passed
    assert check.unverified_figures == ()
    assert check.spelled_numbers == ()


def test_figure_missing_from_facts_is_reported():
    narration = "La hora más barata costará 0,079 €/kWh."

    check = verify_figures(narration, FACTS)

    assert not check.passed
    assert check.unverified_figures == ("0,079",)


def test_reformatted_figure_is_not_accepted():
    narration = "La hora más barata costará 0.082 euros."

    check = verify_figures(narration, FACTS)

    assert check.unverified_figures == ("0.082",)


def test_time_missing_from_facts_is_reported():
    narration = "Pon la lavadora a las 13:00."

    check = verify_figures(narration, FACTS)

    assert check.unverified_figures == ("13:00",)


def test_spelled_out_numbers_are_reported():
    narration = "Ahorrarás hasta veinte euros si cambias tres electrodomésticos de hora."

    check = verify_figures(narration, FACTS)

    assert not check.passed
    assert check.spelled_numbers == ("veinte", "tres")


def test_articles_and_averages_are_not_treated_as_numbers():
    narration = "Una buena idea: de media, un día como mañana sale barato."

    check = verify_figures(narration, FACTS)

    assert check.passed


def test_spelled_numbers_are_detected_case_and_accent_insensitively():
    narration = "Dieciséis horas baratas y DOS caras."

    check = verify_figures(narration, FACTS)

    assert check.spelled_numbers == ("dieciséis", "dos")


def test_proportional_claims_are_reported_as_spelled_numbers():
    narration = "La hora cara cuesta el doble que la barata."

    check = verify_figures(narration, FACTS)

    assert check.spelled_numbers == ("doble",)


def test_repeated_unverified_figure_is_reported_once():
    narration = "Cuesta 0,300 €/kWh. Sí, 0,300 €/kWh."

    check = verify_figures(narration, FACTS)

    assert check.unverified_figures == ("0,300",)
