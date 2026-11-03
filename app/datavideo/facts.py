from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    license: str
    license_verified: bool = False


@dataclass(frozen=True)
class Fact:
    key: str
    statement: str
    source: Source
    as_of: date


def statements(facts: Iterable[Fact]) -> list[str]:
    return [fact.statement for fact in facts]


def unique_sources(facts: Iterable[Fact]) -> tuple[Source, ...]:
    return tuple(dict.fromkeys(fact.source for fact in facts))
