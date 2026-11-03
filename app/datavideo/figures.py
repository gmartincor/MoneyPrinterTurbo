import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

_FIGURE_PATTERN = re.compile(r"\d+(?:[.,:]\d+)*")
_WORD_PATTERN = re.compile(r"[^\W\d_]+")

_SPELLED_NUMBERS = frozenset(
    {
        "cero", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
        "diez", "once", "doce", "trece", "catorce", "quince", "dieciseis",
        "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidos",
        "veintitres", "veinticuatro", "veinticinco", "veintiseis", "veintisiete",
        "veintiocho", "veintinueve", "treinta", "cuarenta", "cincuenta", "sesenta",
        "setenta", "ochenta", "noventa", "cien", "ciento", "doscientos",
        "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos",
        "ochocientos", "novecientos", "mil", "millon", "millones", "doble",
        "triple", "mitad",
    }
)


@dataclass(frozen=True)
class FigureCheck:
    unverified_figures: tuple[str, ...]
    spelled_numbers: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.unverified_figures and not self.spelled_numbers


def verify_figures(narration: str, facts: Iterable[str]) -> FigureCheck:
    allowed_figures = {figure for fact in facts for figure in _FIGURE_PATTERN.findall(fact)}
    unverified = [
        figure for figure in _FIGURE_PATTERN.findall(narration) if figure not in allowed_figures
    ]
    spelled = [
        word.lower()
        for word in _WORD_PATTERN.findall(narration)
        if _strip_accents(word.lower()) in _SPELLED_NUMBERS
    ]
    return FigureCheck(
        unverified_figures=_unique_in_order(unverified),
        spelled_numbers=_unique_in_order(spelled),
    )


def _strip_accents(word: str) -> str:
    decomposed = unicodedata.normalize("NFD", word)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _unique_in_order(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
