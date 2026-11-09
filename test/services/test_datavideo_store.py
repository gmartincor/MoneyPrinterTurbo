import pytest

from app.datavideo.store import PUBLICATION_FILE, open_run, published_story_keys


def test_a_run_lives_in_a_folder_per_channel_and_story(tmp_path):
    run = open_run("tu_dinero_es", "ipc_anual_ccaa_2026_09", tmp_path)

    assert run.directory == tmp_path / "tu_dinero_es" / "ipc_anual_ccaa_2026_09"
    assert run.directory.is_dir()


def test_json_artefacts_round_trip_and_mark_the_step_as_done(tmp_path):
    run = open_run("tu_dinero_es", "story_1", tmp_path)

    assert not run.has("script.json")
    run.write_json("script.json", {"title": "Título", "cifras": ["5,5 %"]})

    assert run.has("script.json")
    assert run.read_json("script.json") == {"title": "Título", "cifras": ["5,5 %"]}


def test_an_empty_file_does_not_count_as_a_finished_step(tmp_path):
    run = open_run("tu_dinero_es", "story_1", tmp_path)
    run.path("final.mp4").write_bytes(b"")

    assert not run.has("final.mp4")


@pytest.mark.parametrize("story_key", ["../escape", "Story", "a/b", ""])
def test_story_keys_that_could_leave_the_runs_folder_are_rejected(tmp_path, story_key):
    with pytest.raises(ValueError, match="key"):
        open_run("tu_dinero_es", story_key, tmp_path)


def test_only_successful_publications_count_as_published(tmp_path):
    open_run("tu_dinero_es", "story_1", tmp_path).write_json(PUBLICATION_FILE, {"success": True})
    open_run("tu_dinero_es", "story_2", tmp_path).write_json(PUBLICATION_FILE, {"success": False})
    open_run("tu_dinero_es", "story_3", tmp_path)

    assert published_story_keys("tu_dinero_es", tmp_path) == {"story_1"}


def test_a_channel_without_runs_has_published_nothing(tmp_path):
    assert published_story_keys("mundo_es", tmp_path) == set()
