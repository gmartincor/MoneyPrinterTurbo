from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    license: str
    license_verified: bool = False
    attribution: str = ""


@dataclass(frozen=True)
class Fact:
    key: str
    statement: str
    source: Source
    as_of: date
    label: str = ""
    value: str = ""
    detail: str = ""


def labelled_fact(key: str, label: str, value: str, source: Source, as_of: date, detail: str = "") -> Fact:
    statement = f"{label}: {detail}, {value}" if detail else f"{label}: {value}"
    return Fact(
        key=key, statement=statement, source=source, as_of=as_of, label=label, value=value, detail=detail
    )


def statements(facts: Iterable[Fact]) -> list[str]:
    return [fact.statement for fact in facts]


def unique_sources(facts: Iterable[Fact]) -> tuple[Source, ...]:
    return tuple(dict.fromkeys(fact.source for fact in facts))
