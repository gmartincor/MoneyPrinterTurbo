import os
from datetime import datetime, timedelta, timezone

from app.datavideo.digest import weekly_digest
from app.datavideo.store import PUBLICATION_FILE, open_run

NOW = datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc)


def run_with(root, story_key, title, published=None, days_ago=1, closing=8):
    run = open_run("tu_dinero_es", story_key, root)
    run.write_json("package.json", {"title": title, "description": "", "tags": []})
    run.write_json("quality.json", {"passed": True, "problems": []})
    scores = {"hook": 8, "interest": 8, "clarity": 8, "rhythm": 8, "closing": closing}
    run.write_json("review.json", {"best": {"scores": scores, "fixes": []}, "rounds": []})
    if published is not None:
        run.write_json(PUBLICATION_FILE, {"success": published, "request_id": "abc", "privacy": "public"})
    moment = (NOW - timedelta(days=days_ago)).timestamp()
    os.utime(run.directory, (moment, moment))
    return run


def test_digest_lists_what_was_published_and_what_was_not(tmp_path):
    run_with(tmp_path, "story_a", "Galicia lidera la inflación", published=True)
    run_with(tmp_path, "story_b", "El paro baja en Madrid", published=False)
    run_with(tmp_path, "story_c", "Vivienda por comunidades")

    digest = weekly_digest("tu_dinero_es", NOW, tmp_path)

    assert "1 publicado" in digest
    assert "2 sin publicar" in digest
    assert "Galicia lidera la inflación" in digest
    assert "El paro baja en Madrid" in digest


def test_runs_older_than_a_week_are_left_out(tmp_path):
    run_with(tmp_path, "story_old", "Vídeo antiguo", published=True, days_ago=9)

    digest = weekly_digest("tu_dinero_es", NOW, tmp_path)

    assert "Vídeo antiguo" not in digest
    assert "0 publicados" in digest


def test_a_quiet_week_still_produces_a_digest(tmp_path):
    digest = weekly_digest("tu_dinero_es", NOW, tmp_path)

    assert digest.startswith("Resumen semanal de tu_dinero_es")
    assert "0 publicados" in digest


def test_scripts_held_by_the_editor_are_listed_with_their_weakest_criterion(tmp_path):
    run_with(tmp_path, "story_held", "Paro juvenil por comunidades", closing=6)

    digest = weekly_digest("tu_dinero_es", NOW, tmp_path)

    assert "1 retenido por el editor" in digest
    assert "Retenido por el editor: Paro juvenil por comunidades (closing 6/10)" in digest
