from datetime import date
from decimal import ROUND_HALF_UP, Decimal

SPANISH_SPAIN = "es-ES"
ENGLISH_US = "en-US"
SUPPORTED_LOCALES = (SPANISH_SPAIN, ENGLISH_US)

_SPANISH_GROUPING_THRESHOLD = Decimal(10000)
_WEEKDAYS = {
    SPANISH_SPAIN: ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"),
    ENGLISH_US: ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}
_MONTHS = {
    SPANISH_SPAIN: (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ),
    ENGLISH_US: (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ),
}


def format_decimal(value: Decimal, places: int, locale: str) -> str:
    _require_supported(locale)
    rounded = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    if locale == ENGLISH_US:
        return f"{rounded:,.{places}f}"
    if abs(rounded) < _SPANISH_GROUPING_THRESHOLD:
        return f"{rounded:.{places}f}".replace(".", ",")
    english_grouped = f"{rounded:,.{places}f}"
    return english_grouped.replace(",", "\0").replace(".", ",").replace("\0", ".")


def format_percent(value: Decimal, places: int, locale: str) -> str:
    number = format_decimal(value, places, locale)
    return f"{number} %" if locale == SPANISH_SPAIN else f"{number}%"


def format_long_date(day: date, locale: str) -> str:
    _require_supported(locale)
    weekday = _WEEKDAYS[locale][day.weekday()]
    month = _MONTHS[locale][day.month - 1]
    if locale == SPANISH_SPAIN:
        return f"{weekday} {day.day} de {month} de {day.year}"
    return f"{weekday}, {month} {day.day}, {day.year}"


def format_month(year: int, month: int, locale: str) -> str:
    _require_supported(locale)
    name = _MONTHS[locale][month - 1]
    return f"{name} de {year}" if locale == SPANISH_SPAIN else f"{name} {year}"


def _require_supported(locale: str) -> None:
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(f"unsupported locale: {locale}")
