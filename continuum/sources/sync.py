"""Incremental sync cursor persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path

from continuum.sources.cursor import SyncCursor


def load_cursor(path: Path) -> SyncCursor:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SyncCursor.from_dict(data)


def save_cursor(cursor: SyncCursor, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write-temp-then-rename: a crash mid-write must never corrupt the cursor.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cursor.to_dict(), indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
