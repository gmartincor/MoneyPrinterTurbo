import re
import subprocess
from pathlib import Path

from app.services.video import get_ffmpeg_binary

TARGET_LOUDNESS = -14.0
TRUE_PEAK = -1.5
_INTEGRATED_LOUDNESS = re.compile(r"I:\s+(-?\d+(?:\.\d+)?) LUFS")


def normalize_loudness(source: Path, target: Path) -> Path:
    subprocess.run(
        [
            get_ffmpeg_binary(), "-v", "error", "-y", "-i", str(source),
            "-af", f"loudnorm=I={TARGET_LOUDNESS}:TP={TRUE_PEAK}:LRA=11",
            "-ar", "48000", str(target),
        ],
        check=True,
    )
    return target


def measure_loudness(media: Path) -> float:
    result = subprocess.run(
        [get_ffmpeg_binary(), "-nostats", "-hide_banner", "-i", str(media), "-map", "0:a:0", "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    matches = _INTEGRATED_LOUDNESS.findall(result.stderr)
    if result.returncode != 0 or not matches:
        raise RuntimeError(f"could not measure the loudness of {media.name}")
    return float(matches[-1])
