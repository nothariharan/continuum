"""Event queue for continuous memory ingestion."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceEvent:
    event_id: str
    source: str
    event_type: str
    native_id: str | None
    payload: dict[str, Any]
    received_at: str
    status: str = "pending"
    attempts: int = 0

    @property
    def dedup_key(self) -> str:
        return f"{self.source}|{self.native_id or ''}"


@dataclass
class EventQueue:
    path: Path
    _seen: set[str] = field(default_factory=set, repr=False)
    _loaded: bool = False

    def load(self) -> list[SourceEvent]:
        self._loaded = True
        if not self.path.exists():
            return []
        events: list[SourceEvent] = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                event = SourceEvent(**row)
            except (json.JSONDecodeError, TypeError) as exc:
                # Partial-write tolerance: a crash mid-append leaves a trailing
                # malformed line. Skip it — Slack redelivers the record, so the
                # queue must not wedge on a truncated tail.
                logger.warning("event_queue skipping malformed line %s in %s: %s", line_number, self.path, exc)
                continue
            events.append(event)
            self._seen.add(event.event_id)
            self._seen.add(event.dedup_key)
        return events

    def enqueue(self, event: SourceEvent) -> bool:
        """Return False if duplicate (by event_id or source/native record)."""
        if not self._loaded:
            self.load()
        if event.dedup_key in self._seen or event.event_id in self._seen:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        self._seen.add(event.event_id)
        self._seen.add(event.dedup_key)
        return True

    def mark_processed(self, event_id: str, *, status: str = "processed", attempts: int | None = None) -> None:
        events = self.load()
        updated: list[SourceEvent] = []
        for event in events:
            if event.event_id == event_id:
                updated.append(
                    SourceEvent(
                        event_id=event.event_id,
                        source=event.source,
                        event_type=event.event_type,
                        native_id=event.native_id,
                        payload=event.payload,
                        received_at=event.received_at,
                        status=status,
                        attempts=attempts if attempts is not None else event.attempts,
                    )
                )
            else:
                updated.append(event)
        # Write-temp-then-rename so a crash mid-write never truncates the queue.
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for event in updated:
                handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        os.replace(tmp, self.path)
