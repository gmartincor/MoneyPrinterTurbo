import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.utils import utils

PUBLICATION_FILE = "publication.json"
_SAFE_KEY = re.compile(r"^[a-z0-9_]+$")


def runs_root() -> Path:
    return Path(utils.storage_dir("datavideo"))


@dataclass(frozen=True)
class Run:
    directory: Path

    @property
    def story_key(self) -> str:
        return self.directory.name

    def path(self, name: str) -> Path:
        return self.directory / name

    def has(self, name: str) -> bool:
        artefact = self.path(name)
        return artefact.is_file() and artefact.stat().st_size > 0

    def read_json(self, name: str) -> Any:
        return json.loads(self.path(name).read_text(encoding="utf-8"))

    def write_json(self, name: str, data: Any) -> Path:
        target = self.path(name)
        handle, temporary = tempfile.mkstemp(dir=self.directory, prefix=f".{name}.", suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
        return target


def open_run(channel_id: str, story_key: str, root: Path | None = None) -> Run:
    for key in (channel_id, story_key):
        if not _SAFE_KEY.match(key):
            raise ValueError(f"invalid run key: {key!r}")
    directory = (root or runs_root()) / channel_id / story_key
    directory.mkdir(parents=True, exist_ok=True)
    return Run(directory=directory)


def published_story_keys(channel_id: str, root: Path | None = None) -> set[str]:
    channel_directory = (root or runs_root()) / channel_id
    if not channel_directory.is_dir():
        return set()
    published = set()
    for directory in channel_directory.iterdir():
        publication = directory / PUBLICATION_FILE
        if publication.is_file() and json.loads(publication.read_text(encoding="utf-8")).get("success") is True:
            published.add(directory.name)
    return published
