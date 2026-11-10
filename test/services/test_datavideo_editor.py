import json
from datetime import date

import pytest

from app.datavideo.editor import CRITERIA, MINIMUM_SCORE, TARGET_SCORE, Review, review_from_dict, review_script
from app.datavideo.facts import labelled_fact
from app.datavideo.locale import SPANISH_SPAIN
from app.datavideo.script import Script, ScriptSegment
from app.datavideo.sources.ine import INE_SOURCE

FACTS = [labelled_fact("highest", "Tasa de paro más alta", "18,87 %", INE_SOURCE, date(2026, 7, 1), "Melilla")]
SCRIPT = Script(
    title="Melilla, 18,87 % de paro",
    segments=(ScriptSegment(text="Melilla: 18,87 % de paro.", fact_keys=("highest",), scene="big_number"),),
)


def scores(value=9, **overrides):
    return {**{criterion: value for criterion in CRITERIA}, **overrides}


def editor_reply(score_values, fixes=("Abre con la cifra de Melilla",)):
    return json.dumps({"scores": score_values, "fixes": list(fixes)}, ensure_ascii=False)


class Editor(list):
    def __init__(self, *replies):
        super().__init__()
        self.replies = list(replies)

    def __call__(self, prompt):
        self.append(prompt)
        return self.replies.pop(0)


def test_the_editor_sees_the_script_and_the_facts_as_data():
    editor = Editor(editor_reply(scores()))

    review_script(SCRIPT, FACTS, "el paro", SPANISH_SPAIN, editor)

    assert "<script>" in editor[0] and "Melilla: 18,87 % de paro." in editor[0]
    assert "[highest] Tasa de paro más alta: Melilla, 18,87 %" in editor[0]
    assert all(criterion in editor[0] for criterion in CRITERIA)


def test_a_review_passes_only_when_every_criterion_reaches_the_target():
    assert Review(scores=scores(), fixes=()).passed is True
    assert Review(scores=scores(hook=TARGET_SCORE - 1), fixes=()).passed is False


def test_a_review_is_publishable_when_every_criterion_reaches_the_minimum():
    assert Review(scores=scores(MINIMUM_SCORE), fixes=()).publishable is True
    assert Review(scores=scores(MINIMUM_SCORE, closing=MINIMUM_SCORE - 1), fixes=()).publishable is False


def test_the_editor_reply_becomes_scores_and_fixes():
    review = review_script(SCRIPT, FACTS, "el paro", SPANISH_SPAIN, Editor(editor_reply(scores(hook=6))))

    assert review.scores["hook"] == 6
    assert review.fixes == ("Abre con la cifra de Melilla",)
    assert review.total == 6 + 9 * (len(CRITERIA) - 1)


def test_a_malformed_editor_reply_is_asked_again():
    editor = Editor("No puedo puntuar esto", editor_reply(scores()))

    review = review_script(SCRIPT, FACTS, "el paro", SPANISH_SPAIN, editor)

    assert review.passed is True
    assert len(editor) == 2


def test_an_editor_that_never_answers_properly_fails_the_review():
    editor = Editor("x", "y", "z")

    review = review_script(SCRIPT, FACTS, "el paro", SPANISH_SPAIN, editor)

    assert review.publishable is False


@pytest.mark.parametrize("bad_scores", [scores(hook=11), {"hook": 9}])
def test_scores_outside_the_scale_or_missing_criteria_are_rejected(bad_scores):
    editor = Editor(editor_reply(bad_scores), editor_reply(scores()))

    review_script(SCRIPT, FACTS, "el paro", SPANISH_SPAIN, editor)

    assert len(editor) == 2


def test_a_saved_review_is_restored_exactly():
    review = Review(scores=scores(hook=7), fixes=("Más corto",))

    assert review_from_dict(json.loads(json.dumps(review.to_dict()))) == review


def test_the_editor_knows_what_the_screen_already_shows():
    editor = Editor(editor_reply(scores()))

    review_script(SCRIPT, FACTS, "el paro", SPANISH_SPAIN, editor)

    assert "already shows the source and the period" in editor[0]
