import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.datavideo.sources.ine import INE_SOURCE, display_region, download_table, parse_table, quarter_of, split_region

FIXTURE = Path(__file__).parent / "fixtures" / "datavideo" / "ine_table_76140.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_every_series_of_the_table_is_parsed_with_its_name_and_values():
    series = parse_table(load_fixture())

    by_name = {item.name: item for item in series}
    andalusia = by_name["Andalucía. Índice general. Variación anual."]
    assert len(series) == 60
    assert andalusia.code == "IPC293659"
    assert [(item.year, item.period, item.value) for item in andalusia.observations] == [(2026, 9, Decimal("4.7"))]


def test_values_keep_their_exact_decimal_digits():
    series = parse_table(load_fixture())

    national = next(item for item in series if item.name == "Nacional. Índice general. Variación anual.")
    assert national.observations[0].value == Decimal("4.9")


def test_secret_and_missing_values_are_dropped():
    payload = [{
        "COD": "X1",
        "Nombre": "Ceuta. Índice general. Variación anual. ",
        "Data": [
            {"Anyo": 2026, "FK_Periodo": 9, "Valor": None, "Secreto": False},
            {"Anyo": 2026, "FK_Periodo": 8, "Valor": 3.0, "Secreto": True},
            {"Anyo": 2026, "FK_Periodo": 7, "Valor": 2.5, "Secreto": False},
        ],
    }]

    observations = parse_table(payload)[0].observations

    assert [(item.period, item.value) for item in observations] == [(7, Decimal("2.5"))]


def test_a_response_with_an_unexpected_shape_is_rejected():
    with pytest.raises(ValueError, match="INE"):
        parse_table({"error": "table not found"})


def test_download_asks_for_the_table_and_the_number_of_periods():
    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return load_fixture()

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return Response()

    payload = download_table(76140, periods=3, get=fake_get)

    assert payload == load_fixture()
    assert calls[0][0].endswith("/DATOS_TABLA/76140")
    assert calls[0][1] == {"nult": 3}
    assert calls[0][2] > 0


@pytest.mark.parametrize(
    "ine_name, display_name",
    [
        ("Madrid, Comunidad de", "Comunidad de Madrid"),
        ("Balears, Illes", "Baleares"),
        ("Castilla - La Mancha", "Castilla-La Mancha"),
        ("Rioja, La", "La Rioja"),
        ("Comunitat Valenciana", "Comunidad Valenciana"),
        ("Andalucía", "Andalucía"),
        ("Nuevo Territorio, El", "El Nuevo Territorio"),
    ],
)
def test_region_names_are_shown_as_people_say_them(ine_name, display_name):
    assert display_region(ine_name) == display_name


def test_the_ine_licence_allows_commercial_use_and_is_verified():
    assert INE_SOURCE.license_verified
    assert "CC BY 4.0" in INE_SOURCE.license


@pytest.mark.parametrize(
    "series_name, expected",
    [
        ("Andalucía. Índice general. Variación anual.", ("Andalucía", "Índice general. Variación anual.")),
        ("Nacional. Transporte. Variación anual. ", ("Nacional", "Transporte. Variación anual.")),
        (
            "Tasa de paro de la población. Ambos sexos. Rioja, La. Total.",
            ("Rioja, La", "Tasa de paro de la población. Ambos sexos. Total."),
        ),
        (
            "Tasa de paro de la población. Ambos sexos. Total Nacional. Total.",
            ("Total Nacional", "Tasa de paro de la población. Ambos sexos. Total."),
        ),
    ],
)
def test_the_region_is_found_wherever_the_ine_puts_it_in_the_series_name(series_name, expected):
    assert split_region(series_name) == expected


def test_a_series_without_a_region_has_no_split():
    assert split_region("Industria. Coste laboral total. Euros.") is None


@pytest.mark.parametrize("period, quarter", [(19, 1), (20, 2), (21, 3), (22, 4)])
def test_ine_quarter_periods_are_read_as_quarters(period, quarter):
    assert quarter_of(period) == quarter


def test_a_period_that_is_not_a_quarter_is_rejected():
    with pytest.raises(ValueError, match="quarter"):
        quarter_of(9)
