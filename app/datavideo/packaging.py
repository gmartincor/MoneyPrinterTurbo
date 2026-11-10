from dataclasses import dataclass
from typing import Sequence

from app.datavideo.facts import Fact, unique_sources
from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.script import Script

INSTAGRAM_CAPTION_LIMIT = 2200
_HASHTAGS_SHOWN = 3
_TEXT = {
    SPANISH_SPAIN: {
        "source": "Fuente: {name}. {attribution}. Datos: {period}.",
        "ai": "Guion generado con IA a partir de datos oficiales. Cada cifra se comprueba automáticamente "
        "contra los datos antes de publicar.",
        "advice": "Contenido informativo: no es asesoramiento financiero.",
    },
    "en-US": {
        "source": "Source: {name}. {attribution}. Data: {period}.",
        "ai": "Script generated with AI from official data. Every figure is checked automatically against "
        "the data before publishing.",
        "advice": "For information only: this is not financial advice.",
    },
}


@dataclass(frozen=True)
class Package:
    title: str
    description: str
    tags: tuple[str, ...]


def build_package(script: Script, facts: Sequence[Fact], period: str, tags: Sequence[str], locale: str) -> Package:
    text = _TEXT[locale]
    source_lines = [
        text["source"].format(name=source.name, attribution=source.attribution or source.url, period=period)
        for source in unique_sources(facts)
    ]
    hashtags = " ".join(f"#{tag.replace(' ', '')}" for tag in tags[:_HASHTAGS_SHOWN])
    description = "\n\n".join([script.narration, *source_lines, text["ai"], text["advice"], hashtags])
    if len(description) > INSTAGRAM_CAPTION_LIMIT:
        raise ValueError(f"description has {len(description)} characters, over the {INSTAGRAM_CAPTION_LIMIT} limit")
    return Package(title=script.title, description=description, tags=tuple(tags))
