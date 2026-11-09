from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from moviepy import VideoFileClip
from PIL import Image

from app.datavideo import render
from app.datavideo.render import TimedScene, compose_video, render_scene_track
from app.datavideo.theme import DEFAULT_THEME
from app.datavideo.timeline import Narration

SMALL_VERTICAL = (180, 320)


@dataclass(frozen=True)
class SolidScene:
    color: tuple[int, int, int]

    def draw(self, size, progress):
        return Image.new("RGB", size, self.color)


def test_scene_track_lasts_the_sum_of_the_segment_durations(tmp_path):
    output = tmp_path / "scenes.mp4"
    timed = [TimedScene(SolidScene((255, 0, 0)), 0.6), TimedScene(SolidScene((0, 0, 255)), 0.9)]

    render_scene_track(timed, output, SMALL_VERTICAL, fps=10)

    with VideoFileClip(str(output)) as clip:
        assert tuple(clip.size) == SMALL_VERTICAL
        assert clip.duration == pytest.approx(1.5, abs=0.15)


def test_each_scene_is_shown_during_its_own_segment(tmp_path):
    output = tmp_path / "scenes.mp4"
    timed = [TimedScene(SolidScene((255, 0, 0)), 0.6), TimedScene(SolidScene((0, 0, 255)), 0.9)]

    render_scene_track(timed, output, SMALL_VERTICAL, fps=10)

    with VideoFileClip(str(output)) as clip:
        first = np.asarray(clip.get_frame(0.3))[160, 90]
        second = np.asarray(clip.get_frame(1.2))[160, 90]
    assert first[0] > 200 and first[2] < 60
    assert second[2] > 200 and second[0] < 60


def test_composition_adds_voice_and_subtitles_without_music(tmp_path, monkeypatch):
    calls = {}
    subtitle = tmp_path / "narration.srt"
    subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n", encoding="utf-8")
    narration = Narration(audio_path=tmp_path / "narration.mp3", subtitle_path=subtitle, durations=(1.0,))

    def fake_generate_video(video_path, audio_path, subtitle_path, output_file, params):
        calls.update(video=video_path, audio=audio_path, subtitle=subtitle_path, output=output_file, params=params)
        return True

    monkeypatch.setattr(render.video, "generate_video", fake_generate_video)

    compose_video(tmp_path / "scenes.mp4", narration, tmp_path / "final.mp4", "9:16", "Título", DEFAULT_THEME)

    params = calls["params"]
    assert calls["audio"] == str(narration.audio_path)
    assert calls["subtitle"] == str(subtitle)
    assert params.bgm_type == ""
    assert params.subtitle_enabled is True
    assert params.font_name == DEFAULT_THEME.font_file
    assert params.video_aspect == "9:16"


def test_composition_without_a_subtitle_file_keeps_the_voice(tmp_path, monkeypatch):
    calls = {}
    narration = Narration(audio_path=tmp_path / "narration.mp3", subtitle_path=tmp_path / "missing.srt", durations=(1.0,))
    monkeypatch.setattr(render.video, "generate_video", lambda **kwargs: calls.update(kwargs) or True)

    compose_video(tmp_path / "scenes.mp4", narration, tmp_path / "final.mp4", "9:16", "Título", DEFAULT_THEME)

    assert calls["subtitle_path"] == ""
    assert calls["params"].subtitle_enabled is False


def test_output_path_is_returned(tmp_path, monkeypatch):
    narration = Narration(audio_path=tmp_path / "a.mp3", subtitle_path=tmp_path / "a.srt", durations=(1.0,))
    monkeypatch.setattr(render.video, "generate_video", lambda **kwargs: True)

    output = compose_video(tmp_path / "s.mp4", narration, tmp_path / "f.mp4", "9:16", "Título", DEFAULT_THEME)

    assert output == Path(tmp_path / "f.mp4")
