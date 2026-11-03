from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.datavideo.electricity import HourlyPrice, describe_day, summarize_day

MADRID_WINTER = timezone(timedelta(hours=1))


def day_of_prices(eur_per_mwh_by_hour):
    midnight = datetime(2026, 11, 4, 0, 0, tzinfo=MADRID_WINTER)
    return [
        HourlyPrice(starts_at=midnight + timedelta(hours=hour), eur_per_mwh=Decimal(price))
        for hour, price in enumerate(eur_per_mwh_by_hour)
    ]


FLAT_PRICES = ["150"] * 24


def test_cheapest_and_most_expensive_hours_are_identified():
    prices = list(FLAT_PRICES)
    prices[14] = "82.4"
    prices[20] = "231.2"

    summary = summarize_day(date(2026, 11, 4), day_of_prices(prices))

    assert summary.cheapest.starts_at.hour == 14
    assert summary.most_expensive.starts_at.hour == 20


def test_cheapest_three_hour_window_minimizes_average_price():
    prices = list(FLAT_PRICES)
    prices[13:16] = ["90", "80", "95"]
    prices[3] = "70"

    summary = summarize_day(date(2026, 11, 4), day_of_prices(prices))

    assert summary.cheapest_window[0].starts_at.hour == 13
    assert len(summary.cheapest_window) == 3


def test_describe_day_formats_facts_in_spanish():
    prices = list(FLAT_PRICES)
    prices[13:16] = ["90", "82.4", "95"]
    prices[20] = "231.2"

    facts = describe_day(summarize_day(date(2026, 11, 4), day_of_prices(prices)))

    assert facts == [
        "Fecha: miércoles 4 de noviembre de 2026",
        "Hora más barata: de 14:00 a 15:00, a 0,082 €/kWh",
        "Hora más cara: de 20:00 a 21:00, a 0,231 €/kWh",
        "Precio medio del día: 0,146 €/kWh",
        "Franja de 3 horas más barata: de 13:00 a 16:00, a una media de 0,089 €/kWh",
        "Diferencia entre la hora más cara y la más barata: 181 %",
        "Fuente: Red Eléctrica, precio PVPC",
    ]


def test_hour_labels_follow_madrid_local_time():
    utc_midnight_of_madrid_day = datetime(2026, 11, 3, 23, 0, tzinfo=timezone.utc)
    prices = [
        HourlyPrice(starts_at=utc_midnight_of_madrid_day + timedelta(hours=hour), eur_per_mwh=Decimal("150"))
        for hour in range(24)
    ]
    prices[0] = HourlyPrice(starts_at=prices[0].starts_at, eur_per_mwh=Decimal("50"))

    facts = describe_day(summarize_day(date(2026, 11, 4), prices))

    assert facts[1] == "Hora más barata: de 00:00 a 01:00, a 0,050 €/kWh"


def test_spring_forward_day_with_23_hours_is_accepted():
    madrid_midnight = datetime(2027, 3, 27, 23, 0, tzinfo=timezone.utc)
    prices = [
        HourlyPrice(starts_at=madrid_midnight + timedelta(hours=hour), eur_per_mwh=Decimal("150"))
        for hour in range(23)
    ]

    summary = summarize_day(date(2027, 3, 28), prices)

    assert len(summary.prices) == 23


def test_percentage_gap_is_omitted_when_cheapest_price_is_not_positive():
    prices = list(FLAT_PRICES)
    prices[14] = "0"

    facts = describe_day(summarize_day(date(2026, 11, 4), day_of_prices(prices)))

    assert not any(fact.startswith("Diferencia") for fact in facts)


@pytest.mark.parametrize("hours", [0, 22, 26])
def test_days_with_impossible_hour_counts_are_rejected(hours):
    with pytest.raises(ValueError, match="hourly prices"):
        summarize_day(date(2026, 11, 4), day_of_prices(["150"] * hours))


def test_prices_for_a_different_day_are_rejected():
    with pytest.raises(ValueError, match="local midnight of 2026-11-05"):
        summarize_day(date(2026, 11, 5), day_of_prices(FLAT_PRICES))


def test_prices_must_be_consecutive_hours():
    prices = day_of_prices(FLAT_PRICES)
    prices[5], prices[6] = prices[6], prices[5]

    with pytest.raises(ValueError, match="consecutive"):
        summarize_day(date(2026, 11, 4), prices)
