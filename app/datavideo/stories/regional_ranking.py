import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Sequence

from app.datavideo.facts import Fact, labelled_fact
from app.datavideo.locale import (
    SPANISH_SPAIN,
    format_decimal,
    format_euros,
    format_month,
    format_percent,
    format_quarter,
)
from app.datavideo.sources.ine import INE_SOURCE, NATIONAL_NAMES, Series, display_region, quarter_of, split_region

AUTONOMOUS_CITIES = frozenset({"Ceuta", "Melilla"})
PERIODS_TO_DOWNLOAD = 3
MONTHLY = "monthly"
QUARTERLY = "quarterly"
PERCENT = "percent"
EUROS = "euros"
_LOCALE = SPANISH_SPAIN
_MONTHS_PER_QUARTER = 3
_PERIOD_LABELS = {MONTHLY: "Mes del dato", QUARTERLY: "Trimestre del dato"}
_SLUG_SEPARATORS = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class RegionalRankingStory:
    key: str
    table_id: int
    measure: str
    indicator: str
    topic: str
    tags: tuple[str, ...] = ()
    higher_is_better: bool = False
    frequency: Literal["monthly", "quarterly"] = MONTHLY
    unit: Literal["percent", "euros"] = PERCENT
    decimal_places: int = 1
    feminine: bool = True


_CPI_TAGS = ("IPC", "inflación", "comunidades autónomas", "INE", "precios", "España")
_EPA_TAGS = ("paro", "EPA", "empleo", "comunidades autónomas", "INE", "España")
_CPI_GROUPS_TABLE = 76136
_EPA_TABLE = 14506

CPI_ANNUAL_BY_REGION = RegionalRankingStory(
    key="ipc_anual_ccaa",
    table_id=76140,
    measure="Índice general. Variación anual.",
    indicator="Inflación anual",
    topic="la inflación anual por comunidades autónomas según el INE",
    tags=("inflación", "IPC", "comunidades autónomas", "INE", "economía", "España"),
)
CPI_FOOD_BY_REGION = RegionalRankingStory(
    key="ipc_alimentos_ccaa",
    table_id=_CPI_GROUPS_TABLE,
    measure="Alimentos y bebidas no alcohólicas. Variación anual.",
    indicator="Inflación de los alimentos",
    topic="cuánto suben en un año los precios de los alimentos y las bebidas no alcohólicas en cada comunidad autónoma, "
    "según el IPC del INE",
    tags=("precio de los alimentos", "cesta de la compra", *_CPI_TAGS),
)
CPI_HOUSING_BY_REGION = RegionalRankingStory(
    key="ipc_vivienda_ccaa",
    table_id=_CPI_GROUPS_TABLE,
    measure="Vivienda, agua, electricidad, gas y otros combustibles. Variación anual.",
    indicator="Inflación de vivienda, agua, luz y gas",
    topic="cuánto suben en un año los precios del grupo vivienda, agua, electricidad, gas y otros combustibles en cada "
    "comunidad autónoma, según el IPC del INE",
    tags=("precio de la luz", "alquiler", "suministros", *_CPI_TAGS),
)
CPI_TRANSPORT_BY_REGION = RegionalRankingStory(
    key="ipc_transporte_ccaa",
    table_id=_CPI_GROUPS_TABLE,
    measure="Transporte. Variación anual.",
    indicator="Inflación del transporte",
    topic="cuánto suben en un año los precios del transporte en cada comunidad autónoma, según el IPC del INE",
    tags=("transporte", "carburantes", *_CPI_TAGS),
)
CPI_RESTAURANTS_BY_REGION = RegionalRankingStory(
    key="ipc_restaurantes_ccaa",
    table_id=_CPI_GROUPS_TABLE,
    measure="Restaurantes y servicios de alojamiento. Variación anual.",
    indicator="Inflación de restaurantes y hoteles",
    topic="cuánto suben en un año los precios de restaurantes y alojamientos en cada comunidad autónoma, "
    "según el IPC del INE",
    tags=("restaurantes", "hoteles", *_CPI_TAGS),
)
UNEMPLOYMENT_BY_REGION = RegionalRankingStory(
    key="paro_ccaa",
    table_id=_EPA_TABLE,
    measure="Tasa de paro de la población. Ambos sexos. Total.",
    indicator="Tasa de paro",
    topic="la tasa de paro por comunidades autónomas según la Encuesta de Población Activa (EPA) del INE",
    tags=_EPA_TAGS,
    frequency=QUARTERLY,
    decimal_places=2,
)
YOUTH_UNEMPLOYMENT_BY_REGION = RegionalRankingStory(
    key="paro_juvenil_ccaa",
    table_id=_EPA_TABLE,
    measure="Tasa de paro de la población. Ambos sexos. Menores de 25 años.",
    indicator="Paro de los menores de 25 años",
    topic="la tasa de paro de los menores de 25 años por comunidades autónomas según la Encuesta de Población Activa "
    "(EPA) del INE",
    tags=("paro juvenil", "jóvenes", *_EPA_TAGS),
    frequency=QUARTERLY,
    decimal_places=2,
    feminine=False,
)
HOUSE_PRICES_BY_REGION = RegionalRankingStory(
    key="precio_vivienda_ccaa",
    table_id=80270,
    measure="General. Variación anual.",
    indicator="Variación anual del precio de la vivienda",
    topic="cuánto cambia en un año el precio de la vivienda libre en cada comunidad autónoma, según el Índice de "
    "Precios de Vivienda (IPV) del INE",
    tags=("precio de la vivienda", "vivienda", "IPV", "comunidades autónomas", "INE", "España"),
    frequency=QUARTERLY,
)
WAGES_BY_REGION = RegionalRankingStory(
    key="salario_ccaa",
    table_id=6061,
    measure="Industria, construcción y servicios (excepto actividades de los hogares como empleadores y de "
    "organizaciones y organismos extraterritoriales). Coste salarial total. Costes laborales. Euros.",
    indicator="Coste salarial por trabajador y mes",
    topic="el coste salarial bruto medio por trabajador y mes en cada comunidad autónoma, según la Encuesta "
    "Trimestral de Coste Laboral (ETCL) del INE",
    tags=("salarios", "sueldo medio", "ETCL", "comunidades autónomas", "INE", "España"),
    higher_is_better=True,
    frequency=QUARTERLY,
    unit=EUROS,
    decimal_places=0,
    feminine=False,
)
STORIES = {
    story.key: story
    for story in (
        CPI_ANNUAL_BY_REGION,
        CPI_FOOD_BY_REGION,
        CPI_HOUSING_BY_REGION,
        CPI_TRANSPORT_BY_REGION,
        CPI_RESTAURANTS_BY_REGION,
        UNEMPLOYMENT_BY_REGION,
        YOUTH_UNEMPLOYMENT_BY_REGION,
        HOUSE_PRICES_BY_REGION,
        WAGES_BY_REGION,
    )
}


@dataclass(frozen=True)
class RegionalValue:
    region: str
    value: Decimal


@dataclass(frozen=True)
class RegionalRanking:
    story: RegionalRankingStory
    year: int
    period: int
    national: Decimal
    previous_national: Decimal | None
    regions: tuple[RegionalValue, ...]

    @property
    def highest(self) -> tuple[RegionalValue, ...]:
        return tuple(item for item in self.regions if item.value == self.regions[0].value)

    @property
    def lowest(self) -> tuple[RegionalValue, ...]:
        return tuple(item for item in self.regions if item.value == self.regions[-1].value)

    @property
    def above_national(self) -> tuple[RegionalValue, ...]:
        return tuple(item for item in self.regions if item.value > self.national)

    @property
    def as_of(self) -> date:
        if self.story.frequency == QUARTERLY:
            return date(self.year, (self.period - 1) * _MONTHS_PER_QUARTER + 1, 1)
        return date(self.year, self.period, 1)

    @property
    def story_key(self) -> str:
        if self.story.frequency == QUARTERLY:
            return f"{self.story.key}_{self.year}_t{self.period}"
        return f"{self.story.key}_{self.year}_{self.period:02d}"

    def period_label(self, locale: str) -> str:
        return _period_label(self.year, self.period, self.story.frequency, locale)


def format_value(story: RegionalRankingStory, value: Decimal, locale: str) -> str:
    if story.unit == EUROS:
        return format_euros(value, story.decimal_places, locale)
    return format_percent(value, story.decimal_places, locale)


def build_ranking(series: Sequence[Series], story: RegionalRankingStory) -> RegionalRanking:
    values_by_region: dict[str, dict[tuple[int, int], Decimal]] = {}
    national_values: dict[tuple[int, int], Decimal] = {}
    for item in series:
        split = split_region(item.name)
        if split is None or split[1] != story.measure:
            continue
        values = {(point.year, _period_number(point.period, story)): point.value for point in item.observations}
        if split[0] in NATIONAL_NAMES:
            national_values = values
        else:
            values_by_region[split[0]] = values
    if not national_values or not values_by_region:
        raise ValueError(f"table {story.table_id} has no national and regional series for {story.measure}")
    shared_periods = set.intersection(*(set(values) for values in values_by_region.values()))
    shared_periods &= set(national_values)
    if not shared_periods:
        raise ValueError(f"no period is published for every region in table {story.table_id}")
    year, period = max(shared_periods)
    regions = sorted(
        (RegionalValue(region=display_region(name), value=values[(year, period)]) for name, values in values_by_region.items()),
        key=lambda item: (-item.value, item.region),
    )
    return RegionalRanking(
        story=story,
        year=year,
        period=period,
        national=national_values[(year, period)],
        previous_national=national_values.get(_previous_period(year, period, story.frequency)),
        regions=tuple(regions),
    )


def describe_ranking(ranking: RegionalRanking, story: RegionalRankingStory) -> list[Fact]:
    indicator = story.indicator
    article, high, low = ("la", "alta", "baja") if story.feminine else ("el", "alto", "bajo")

    def fact(key: str, label: str, value: str, detail: str = "") -> Fact:
        return labelled_fact(key, label, value, INE_SOURCE, ranking.as_of, detail)

    def value_of(amount: Decimal) -> str:
        return format_value(story, amount, _LOCALE)

    facts = [
        fact("period", _PERIOD_LABELS[story.frequency], ranking.period_label(_LOCALE)),
        fact("national", f"{indicator} en España", value_of(ranking.national)),
    ]
    if ranking.previous_national is not None:
        previous_year, previous_period = _previous_period(ranking.year, ranking.period, story.frequency)
        previous_label = _period_label(previous_year, previous_period, story.frequency, _LOCALE)
        facts.append(
            fact("previous_national", f"{indicator} en España, {previous_label}", value_of(ranking.previous_national))
        )
    facts += [
        fact("highest", f"{indicator} más {high}", value_of(ranking.highest[0].value), _names(ranking.highest)),
        fact("lowest", f"{indicator} más {low}", value_of(ranking.lowest[0].value), _names(ranking.lowest)),
        fact(
            "gap",
            f"Diferencia entre {article} {indicator.lower()} más {high} y {article} más {low}",
            _gap(story, ranking.regions[0].value - ranking.regions[-1].value),
        ),
        fact(
            "above_national",
            f"{_territories(ranking.regions)} por encima del dato nacional",
            f"{len(ranking.above_national)} de {len(ranking.regions)}",
        ),
    ]
    facts += [fact(f"region_{_slug(item.region)}", item.region, value_of(item.value)) for item in ranking.regions]
    return facts


def _period_number(ine_period: int, story: RegionalRankingStory) -> int:
    if story.frequency == QUARTERLY:
        return quarter_of(ine_period)
    if not 1 <= ine_period <= 12:
        raise ValueError(f"INE period {ine_period} is not a month")
    return ine_period


def _period_label(year: int, period: int, frequency: str, locale: str) -> str:
    if frequency == QUARTERLY:
        return format_quarter(year, period, locale)
    return format_month(year, period, locale)


def _previous_period(year: int, period: int, frequency: str) -> tuple[int, int]:
    last = 4 if frequency == QUARTERLY else 12
    return (year - 1, last) if period == 1 else (year, period - 1)


def _gap(story: RegionalRankingStory, gap: Decimal) -> str:
    if story.unit == EUROS:
        return format_value(story, gap, _LOCALE)
    return f"{format_decimal(gap, story.decimal_places, _LOCALE)} puntos"


def _territories(regions: Sequence[RegionalValue]) -> str:
    if any(item.region in AUTONOMOUS_CITIES for item in regions):
        return "Comunidades y ciudades autónomas"
    return "Comunidades autónomas"


def _names(regions: Sequence[RegionalValue]) -> str:
    names = [
        f"{item.region} (ciudad autónoma)" if item.region in AUTONOMOUS_CITIES else item.region for item in regions
    ]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"


def _slug(text: str) -> str:
    plain = unicodedata.normalize("NFD", text.lower())
    plain = "".join(character for character in plain if not unicodedata.combining(character))
    return _SLUG_SEPARATORS.sub("_", plain).strip("_")
