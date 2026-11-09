import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from app.datavideo.facts import Fact, labelled_fact
from app.datavideo.locale import SPANISH_SPAIN, format_decimal, format_month, format_percent
from app.datavideo.sources.ine import INE_SOURCE, Series, display_region

NATIONAL_REGION = "Nacional"
AUTONOMOUS_CITIES = frozenset({"Ceuta", "Melilla"})
PERIODS_TO_DOWNLOAD = 3
_LOCALE = SPANISH_SPAIN
_DECIMAL_PLACES = 1
_SLUG_SEPARATORS = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class RegionalRankingStory:
    key: str
    table_id: int
    measure: str
    indicator: str
    topic: str
    higher_is_better: bool = False


CPI_ANNUAL_BY_REGION = RegionalRankingStory(
    key="ipc_anual_ccaa",
    table_id=76140,
    measure="Índice general. Variación anual.",
    indicator="Inflación anual",
    topic="la inflación anual por comunidades autónomas según el INE",
)


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
        return date(self.year, self.period, 1)

    @property
    def story_key(self) -> str:
        return f"{self.story.key}_{self.year}_{self.period:02d}"


def build_ranking(series: Sequence[Series], story: RegionalRankingStory) -> RegionalRanking:
    values_by_region = {
        _region_of(item.name): {(point.year, point.period): point.value for point in item.observations}
        for item in series
        if _measure_of(item.name) == story.measure
    }
    national_values = values_by_region.pop(NATIONAL_REGION, None)
    if not national_values or not values_by_region:
        raise ValueError(f"table {story.table_id} has no national and regional series for {story.measure}")
    shared_months = set.intersection(*(set(values) for values in values_by_region.values()))
    shared_months &= set(national_values)
    if not shared_months:
        raise ValueError(f"no month is published for every region in table {story.table_id}")
    year, period = max(shared_months)
    regions = sorted(
        (RegionalValue(region=display_region(name), value=values[(year, period)]) for name, values in values_by_region.items()),
        key=lambda item: (-item.value, item.region),
    )
    return RegionalRanking(
        story=story,
        year=year,
        period=period,
        national=national_values[(year, period)],
        previous_national=national_values.get(_previous_month(year, period)),
        regions=tuple(regions),
    )


def describe_ranking(ranking: RegionalRanking, story: RegionalRankingStory) -> list[Fact]:
    indicator = story.indicator
    as_of = ranking.as_of

    def fact(key: str, label: str, value: str, detail: str = "") -> Fact:
        return labelled_fact(key, label, value, INE_SOURCE, as_of, detail)

    gap = ranking.regions[0].value - ranking.regions[-1].value
    facts = [
        fact("period", "Mes del dato", format_month(ranking.year, ranking.period, _LOCALE)),
        fact("national", f"{indicator} en España", _percent(ranking.national)),
    ]
    if ranking.previous_national is not None:
        previous_year, previous_period = _previous_month(ranking.year, ranking.period)
        facts.append(
            fact(
                "previous_national",
                f"{indicator} en España en {format_month(previous_year, previous_period, _LOCALE)}",
                _percent(ranking.previous_national),
            )
        )
    facts += [
        fact("highest", f"{indicator} más alta", _percent(ranking.highest[0].value), _names(ranking.highest)),
        fact("lowest", f"{indicator} más baja", _percent(ranking.lowest[0].value), _names(ranking.lowest)),
        fact(
            "gap",
            f"Diferencia entre la {indicator.lower()} más alta y la más baja",
            f"{format_decimal(gap, _DECIMAL_PLACES, _LOCALE)} puntos",
        ),
        fact(
            "above_national",
            "Comunidades y ciudades autónomas por encima del dato nacional",
            f"{len(ranking.above_national)} de {len(ranking.regions)}",
        ),
    ]
    facts += [fact(f"region_{_slug(item.region)}", item.region, _percent(item.value)) for item in ranking.regions]
    return facts


def _region_of(series_name: str) -> str:
    return series_name.split(".", 1)[0].strip()


def _measure_of(series_name: str) -> str:
    parts = series_name.split(". ", 1)
    return parts[1].strip() if len(parts) == 2 else ""


def _previous_month(year: int, period: int) -> tuple[int, int]:
    return (year - 1, 12) if period == 1 else (year, period - 1)


def _percent(value: Decimal) -> str:
    return format_percent(value, _DECIMAL_PLACES, _LOCALE)


def _names(regions: Sequence[RegionalValue]) -> str:
    names = [
        f"{item.region} (ciudad autónoma)" if item.region in AUTONOMOUS_CITIES else item.region for item in regions
    ]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"


def _slug(text: str) -> str:
    plain = unicodedata.normalize("NFD", text.lower())
    plain = "".join(character for character in plain if not unicodedata.combining(character))
    return _SLUG_SEPARATORS.sub("_", plain).strip("_")
