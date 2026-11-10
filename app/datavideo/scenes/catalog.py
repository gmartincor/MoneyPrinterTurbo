from dataclasses import dataclass
from typing import Mapping, Sequence

from app.datavideo.facts import Fact, Source
from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.scenes.base import Scene
from app.datavideo.scenes.figures import BigNumberScene
from app.datavideo.scenes.ranking import RankingScene, extreme_colors
from app.datavideo.stories.regional_ranking import RegionalRanking
from app.datavideo.theme import Color, Theme

RANKING = "ranking"
BIG_NUMBER = "big_number"

SCENE_DESCRIPTIONS = {
    RANKING: "Animated bar chart ranking every region from highest to lowest, with the national figure marked. "
    "Use it while the narration compares regions",
    BIG_NUMBER: "One figure shown very large with its label. Use it for a segment about one fact, "
    "and list that fact first in the segment",
}
FACT_SCENES = frozenset({BIG_NUMBER})
_CREDIT_TEMPLATES = {SPANISH_SPAIN: "Fuente: {source} · {period}", "en-US": "Source: {source} · {period}"}


@dataclass(frozen=True)
class SceneContext:
    ranking: RegionalRanking
    facts: Mapping[str, Fact]
    theme: Theme
    locale: str


def build_scene(scene_id: str, fact_keys: Sequence[str], context: SceneContext) -> Scene:
    if scene_id == RANKING:
        return RankingScene(
            ranking=context.ranking, theme=context.theme, locale=context.locale, focus=_focus(fact_keys, context)
        )
    if scene_id == BIG_NUMBER:
        known_keys = [key for key in fact_keys if key in context.facts]
        if not known_keys:
            raise ValueError("big_number scene needs at least one known fact")
        fact = context.facts[known_keys[0]]
        return BigNumberScene(fact=fact, color=_fact_color(fact.key, context), theme=context.theme)
    raise ValueError(f"unknown scene: {scene_id}")


def _focus(fact_keys: Sequence[str], context: SceneContext) -> frozenset[str]:
    ranking = context.ranking
    groups = {
        "highest": ranking.highest,
        "lowest": ranking.lowest,
        "gap": ranking.highest + ranking.lowest,
        "above_national": ranking.above_national,
    }
    regions = {item.region for key in fact_keys for item in groups.get(key, ())}
    regions |= {context.facts[key].label for key in fact_keys if key.startswith("region_") and key in context.facts}
    return frozenset(regions)


def _fact_color(fact_key: str, context: SceneContext) -> Color:
    highest_color, lowest_color = extreme_colors(context.ranking, context.theme)
    return {"highest": highest_color, "lowest": lowest_color}.get(fact_key, context.theme.text)


def credit_line(source: Source, period: str, locale: str) -> str:
    return _CREDIT_TEMPLATES[locale].format(source=source.name, period=period)
