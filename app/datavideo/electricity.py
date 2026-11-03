from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
CHEAPEST_WINDOW_HOURS = 3
SOURCE_FACT = "Fuente: Red Eléctrica, precio PVPC"

_ONE_HOUR = timedelta(hours=1)
_KWH_PER_MWH = Decimal(1000)
_HOURS_IN_A_DAY = range(23, 26)
_WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


@dataclass(frozen=True)
class HourlyPrice:
    starts_at: datetime
    eur_per_mwh: Decimal

    @property
    def eur_per_kwh(self) -> Decimal:
        return self.eur_per_mwh / _KWH_PER_MWH


@dataclass(frozen=True)
class DailyElectricitySummary:
    day: date
    prices: tuple[HourlyPrice, ...]
    cheapest: HourlyPrice
    most_expensive: HourlyPrice
    average_eur_per_kwh: Decimal
    cheapest_window: tuple[HourlyPrice, ...]


def summarize_day(day: date, prices: Iterable[HourlyPrice]) -> DailyElectricitySummary:
    ordered = tuple(prices)
    _validate_day(day, ordered)
    windows = [
        ordered[start:start + CHEAPEST_WINDOW_HOURS]
        for start in range(len(ordered) - CHEAPEST_WINDOW_HOURS + 1)
    ]
    return DailyElectricitySummary(
        day=day,
        prices=ordered,
        cheapest=min(ordered, key=lambda price: price.eur_per_mwh),
        most_expensive=max(ordered, key=lambda price: price.eur_per_mwh),
        average_eur_per_kwh=_average_eur_per_kwh(ordered),
        cheapest_window=min(windows, key=_average_eur_per_kwh),
    )


def describe_day(summary: DailyElectricitySummary) -> list[str]:
    window = summary.cheapest_window
    facts = [
        f"Fecha: {_spanish_date(summary.day)}",
        f"Hora más barata: {_time_range(summary.cheapest, summary.cheapest)}, "
        f"a {_format_eur_per_kwh(summary.cheapest.eur_per_kwh)}",
        f"Hora más cara: {_time_range(summary.most_expensive, summary.most_expensive)}, "
        f"a {_format_eur_per_kwh(summary.most_expensive.eur_per_kwh)}",
        f"Precio medio del día: {_format_eur_per_kwh(summary.average_eur_per_kwh)}",
        f"Franja de {CHEAPEST_WINDOW_HOURS} horas más barata: {_time_range(window[0], window[-1])}, "
        f"a una media de {_format_eur_per_kwh(_average_eur_per_kwh(window))}",
    ]
    gap = _percentage_gap(summary)
    if gap is not None:
        facts.append(f"Diferencia entre la hora más cara y la más barata: {gap} %")
    facts.append(SOURCE_FACT)
    return facts


def local_hour_label(moment: datetime) -> str:
    return moment.astimezone(MADRID).strftime("%H:%M")


def _validate_day(day: date, prices: tuple[HourlyPrice, ...]) -> None:
    if len(prices) not in _HOURS_IN_A_DAY:
        raise ValueError(f"expected 23 to 25 hourly prices, got {len(prices)}")
    first_local_start = prices[0].starts_at.astimezone(MADRID)
    if first_local_start.date() != day or first_local_start.hour != 0:
        raise ValueError(f"hourly prices must start at local midnight of {day.isoformat()}")
    for previous, current in zip(prices, prices[1:]):
        if current.starts_at - previous.starts_at != _ONE_HOUR:
            raise ValueError("hourly prices must be consecutive hours")


def _average_eur_per_kwh(prices: tuple[HourlyPrice, ...]) -> Decimal:
    return sum((price.eur_per_kwh for price in prices), Decimal(0)) / len(prices)


def _percentage_gap(summary: DailyElectricitySummary) -> Optional[str]:
    cheapest = summary.cheapest.eur_per_mwh
    if cheapest <= 0:
        return None
    gap = (summary.most_expensive.eur_per_mwh - cheapest) / cheapest * 100
    return str(gap.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _time_range(first: HourlyPrice, last: HourlyPrice) -> str:
    return f"de {local_hour_label(first.starts_at)} a {local_hour_label(last.starts_at + _ONE_HOUR)}"


def _format_eur_per_kwh(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return f"{str(rounded).replace('.', ',')} €/kWh"


def _spanish_date(day: date) -> str:
    return f"{_WEEKDAYS[day.weekday()]} {day.day} de {_MONTHS[day.month - 1]} de {day.year}"
