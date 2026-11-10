from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.datavideo.facts import Source

TEMPUS_URL = "https://servicios.ine.es/wstempus/js/ES"
REQUEST_TIMEOUT_SECONDS = 30
INE_SOURCE = Source(
    name="INE",
    url="https://www.ine.es",
    license="CC BY 4.0, uso comercial permitido citando la fuente (aviso legal del INE)",
    license_verified=True,
    attribution="Elaboración propia con datos extraídos del sitio web del INE: www.ine.es",
)

_REGION_DISPLAY_NAMES = {
    "Asturias, Principado de": "Asturias",
    "Balears, Illes": "Baleares",
    "Castilla - La Mancha": "Castilla-La Mancha",
    "Comunitat Valenciana": "Comunidad Valenciana",
    "Murcia, Región de": "Región de Murcia",
    "Navarra, Comunidad Foral de": "Navarra",
}
NATIONAL_NAMES = frozenset({"Nacional", "Total Nacional"})
REGION_NAMES = frozenset(
    {
        "Andalucía",
        "Aragón",
        "Asturias, Principado de",
        "Balears, Illes",
        "Canarias",
        "Cantabria",
        "Castilla - La Mancha",
        "Castilla y León",
        "Cataluña",
        "Ceuta",
        "Comunitat Valenciana",
        "Extremadura",
        "Galicia",
        "Madrid, Comunidad de",
        "Melilla",
        "Murcia, Región de",
        "Navarra, Comunidad Foral de",
        "País Vasco",
        "Rioja, La",
    }
)
_FIRST_QUARTER_PERIOD = 19
_QUARTERS_PER_YEAR = 4


@dataclass(frozen=True)
class Observation:
    year: int
    period: int
    value: Decimal


@dataclass(frozen=True)
class Series:
    code: str
    name: str
    observations: tuple[Observation, ...]


class _ObservationPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    year: int = Field(alias="Anyo")
    period: int = Field(alias="FK_Periodo")
    value: float | None = Field(alias="Valor")
    secret: bool = Field(default=False, alias="Secreto")


class _SeriesPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str = Field(alias="COD")
    name: str = Field(alias="Nombre")
    data: list[_ObservationPayload] = Field(alias="Data")


def download_table(table_id: int, periods: int, get: Callable[..., Any] = requests.get) -> Any:
    response = get(f"{TEMPUS_URL}/DATOS_TABLA/{table_id}", params={"nult": periods}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def parse_table(payload: Any) -> tuple[Series, ...]:
    if not isinstance(payload, list):
        raise ValueError("INE table response is not a list of series")
    try:
        parsed = [_SeriesPayload.model_validate(item) for item in payload]
    except ValidationError as error:
        raise ValueError(f"INE table response has an unexpected shape: {error}") from error
    return tuple(
        Series(
            code=item.code,
            name=item.name.strip(),
            observations=tuple(
                Observation(year=point.year, period=point.period, value=Decimal(str(point.value)))
                for point in item.data
                if point.value is not None and not point.secret
            ),
        )
        for item in parsed
    )


def display_region(ine_name: str) -> str:
    name = ine_name.strip()
    if name in _REGION_DISPLAY_NAMES:
        return _REGION_DISPLAY_NAMES[name]
    if ", " in name:
        main, article = name.split(", ", 1)
        return f"{article} {main}"
    return name


def split_region(series_name: str) -> tuple[str, str] | None:
    parts = [part.strip().rstrip(".").strip() for part in series_name.strip().split(". ")]
    places = [part for part in parts if part in NATIONAL_NAMES or part in REGION_NAMES]
    if len(places) != 1:
        return None
    measure = ". ".join(part for part in parts if part and part != places[0])
    return places[0], f"{measure}."


def quarter_of(period: int) -> int:
    quarter = period - _FIRST_QUARTER_PERIOD + 1
    if not 1 <= quarter <= _QUARTERS_PER_YEAR:
        raise ValueError(f"INE period {period} is not a quarter")
    return quarter
