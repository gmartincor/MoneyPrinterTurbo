import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.config import config
from app.services import voice

AUDIO_FILE_NAME = "narration.mp3"
SUBTITLE_FILE_NAME = "narration.srt"
_TICKS_PER_SECOND = 10_000_000


@dataclass(frozen=True)
class Narration:
    audio_path: Path
    subtitle_path: Path
    durations: tuple[float, ...]


def use_azure_key_from_environment() -> None:
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    if key and not str(config.azure.get("speech_key", "") or "").strip():
        config.azure["speech_key"] = key


def narrate(segment_texts: Sequence[str], voice_name: str, rate: float, directory: Path) -> Narration:
    use_azure_key_from_environment()
    audio_path = directory / AUDIO_FILE_NAME
    subtitle_path = directory / SUBTITLE_FILE_NAME
    text = " ".join(segment_texts)
    sub_maker = voice.tts(text=text, voice_name=voice_name, voice_rate=rate, voice_file=str(audio_path))
    if sub_maker is None or not sub_maker.subs:
        raise RuntimeError(f"the voice {voice_name} returned no audio")
    voice.create_subtitle(sub_maker=sub_maker, text=text, subtitle_file=str(subtitle_path))
    total_seconds = voice.get_audio_duration(str(audio_path))
    durations = segment_durations(segment_texts, sub_maker.subs, sub_maker.offset, total_seconds)
    return Narration(audio_path=audio_path, subtitle_path=subtitle_path, durations=tuple(durations))


def segment_durations(
    segment_texts: Sequence[str],
    word_texts: Sequence[str],
    word_offsets: Sequence[tuple[int, int]],
    total_seconds: float,
) -> list[float]:
    normalized_segments = [_letters_and_digits(text) for text in segment_texts]
    segment_ends = [sum(len(item) for item in normalized_segments[: index + 1]) for index in range(len(segment_texts))]
    full_text = "".join(normalized_segments)
    spoken: list[tuple[float, float] | None] = [None] * len(segment_texts)
    cursor = 0
    current_segment = None
    for word, (start, end) in zip(word_texts, word_offsets):
        normalized = _letters_and_digits(word)
        if normalized:
            position = full_text.find(normalized, cursor)
            if position < 0:
                continue
            cursor = position + len(normalized)
            current_segment = next(index for index, limit in enumerate(segment_ends) if position < limit)
        if current_segment is None:
            continue
        first_start = spoken[current_segment][0] if spoken[current_segment] else start
        spoken[current_segment] = (first_start, end)
    for number, times in enumerate(spoken, start=1):
        if times is None:
            raise ValueError(f"segment {number} has no spoken words in the narration")
    cuts = [0.0]
    for current, following in zip(spoken, spoken[1:]):
        cuts.append((current[1] + following[0]) / 2 / _TICKS_PER_SECOND)
    cuts.append(total_seconds)
    return [end - start for start, end in zip(cuts, cuts[1:])]


def _letters_and_digits(text: str) -> str:
    plain = unicodedata.normalize("NFD", text.lower())
    return "".join(character for character in plain if character.isalnum() and not unicodedata.combining(character))
