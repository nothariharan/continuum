"""Source-independent synchronization lifecycle."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from continuum.dataset.artifact import Artifact, artifact_to_dict
from continuum.sources.connector import SourceConnector
from continuum.sources.cursor import SyncCursor
from continuum.sources.sync import load_cursor, save_cursor


@dataclass
class SyncHealth:
    source: str
    ok: bool
    detail: str
    cursor: SyncCursor | None = None


@dataclass
class SyncResult:
    artifacts: list[Artifact] = field(default_factory=list)
    next_cursor: SyncCursor | None = None
    fetched: int = 0


class SyncLifecycle(Protocol):
    source: str

    def initial_sync(self, *, limit: int = 100) -> SyncResult: ...

    def incremental_sync(self, cursor: SyncCursor | None, *, limit: int = 100) -> SyncResult: ...

    def fetch_record(self, native_id: str) -> Artifact | None: ...

    def source_health(self) -> SyncHealth: ...


class ConnectorSyncLifecycle:
    """SyncLifecycle wrapper over any SourceConnector."""

    def __init__(self, connector: SourceConnector, *, cursor_path: Path | None = None) -> None:
        self._connector = connector
        self._cursor_path = cursor_path
        self.source = connector.source
        self._seen: set[str] = set()

    def _persist(self, cursor: SyncCursor | None) -> None:
        if cursor and self._cursor_path:
            save_cursor(cursor, self._cursor_path)

    def _load(self) -> SyncCursor | None:
        if self._cursor_path and self._cursor_path.exists():
            return load_cursor(self._cursor_path)
        return None

    def initial_sync(self, *, limit: int = 100) -> SyncResult:
        self._connector.authenticate()
        result = self._connector.fetch(cursor=None, limit=limit)
        artifacts = [self._connector.normalize(r) for r in result.records]
        self._seen = {a.id for a in artifacts}
        self._persist(result.next_cursor or (self._connector.cursor(result.records[-1]) if result.records else None))
        return SyncResult(artifacts=artifacts, next_cursor=result.next_cursor, fetched=len(artifacts))

    def incremental_sync(self, cursor: SyncCursor | None = None, *, limit: int = 100) -> SyncResult:
        self._connector.authenticate()
        cursor = cursor or self._load()
        result = self._connector.fetch(cursor=cursor, limit=limit)
        artifacts: list[Artifact] = []
        for raw in result.records:
            artifact = self._connector.normalize(raw)
            if artifact.id in self._seen:
                continue
            self._seen.add(artifact.id)
            artifacts.append(artifact)
        next_cursor = result.next_cursor
        if result.records:
            next_cursor = next_cursor or self._connector.cursor(result.records[-1])
        self._persist(next_cursor)
        return SyncResult(artifacts=artifacts, next_cursor=next_cursor, fetched=len(artifacts))

    def fetch_record(self, native_id: str) -> Artifact | None:
        self._connector.authenticate()
        if hasattr(self._connector, "fetch_record"):
            raw = self._connector.fetch_record(native_id)  # type: ignore[attr-defined]
            return self._connector.normalize(raw) if raw is not None else None
        for raw in self._connector.fetch(cursor=None, limit=10_000).records:
            artifact = self._connector.normalize(raw)
            if artifact.source_id == native_id:
                return artifact
        return None

    def source_health(self) -> SyncHealth:
        try:
            self._connector.authenticate()
            return SyncHealth(source=self.source, ok=True, detail="authenticated", cursor=self._load())
        except Exception as exc:
            return SyncHealth(source=self.source, ok=False, detail=str(exc))


def write_artifacts_jsonl(artifacts: list[Artifact], path: Path, *, append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        for artifact in artifacts:
            handle.write(json.dumps(artifact_to_dict(artifact), ensure_ascii=False) + "\n")
