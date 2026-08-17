"""Incremental sync cursor persistence."""

from __future__ import annotations

import json
from pathlib import Path

from continuum.sources.cursor import SyncCursor


def load_cursor(path: Path) -> SyncCursor:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SyncCursor.from_dict(data)


def save_cursor(cursor: SyncCursor, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cursor.to_dict(), indent=2) + "\n", encoding="utf-8")
