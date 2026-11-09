from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.datavideo.store import PUBLICATION_FILE, Run, runs_root

DIGEST_DAYS = 7
_PACKAGE_FILE = "package.json"


def weekly_digest(channel_id: str, now: datetime, root: Path | None = None) -> str:
    channel_directory = (root or runs_root()) / channel_id
    since = now - timedelta(days=DIGEST_DAYS)
    published, pending = [], []
    if channel_directory.is_dir():
        for directory in sorted(channel_directory.iterdir()):
            if not directory.is_dir():
                continue
            if datetime.fromtimestamp(directory.stat().st_mtime, tz=timezone.utc) < since:
                continue
            run = Run(directory=directory)
            title = run.read_json(_PACKAGE_FILE)["title"] if run.has(_PACKAGE_FILE) else run.story_key
            succeeded = run.has(PUBLICATION_FILE) and run.read_json(PUBLICATION_FILE).get("success") is True
            (published if succeeded else pending).append(title)
    lines = [
        f"Resumen semanal de {channel_id}: {_count(len(published), 'publicado', 'publicados')}, "
        f"{len(pending)} sin publicar."
    ]
    lines += [f"Publicado: {title}" for title in published]
    lines += [f"Sin publicar: {title}" for title in pending]
    return "\n".join(lines)


def _count(number: int, singular: str, plural: str) -> str:
    return f"{number} {singular if number == 1 else plural}"
