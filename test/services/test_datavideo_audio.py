import subprocess

import pytest

from app.datavideo.audio import TARGET_LOUDNESS, measure_loudness, normalize_loudness
from app.services.video import get_ffmpeg_binary


def quiet_tone(path):
    subprocess.run(
        [
            get_ffmpeg_binary(), "-v", "error", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=4", "-af", "volume=0.05", str(path),
        ],
        check=True,
    )
    return path


def test_quiet_audio_is_brought_to_the_target_loudness(tmp_path):
    source = quiet_tone(tmp_path / "quiet.mp3")

    normalized = normalize_loudness(source, tmp_path / "normalized.mp3")

    assert measure_loudness(source) < TARGET_LOUDNESS - 6
    assert measure_loudness(normalized) == pytest.approx(TARGET_LOUDNESS, abs=1.5)


def test_measuring_a_file_without_audio_fails_loudly(tmp_path):
    silent_video = tmp_path / "video.mp4"
    subprocess.run(
        [get_ffmpeg_binary(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1", str(silent_video)],
        check=True,
    )

    with pytest.raises(RuntimeError, match="loudness"):
        measure_loudness(silent_video)
