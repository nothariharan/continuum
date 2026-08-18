"""Event queue for continuous memory ingestion."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceEvent:
    event_id: str
    source: str
    event_type: str
    native_id: str | None
    payload: dict[str, Any]
    received_at: str
    status: str = "pending"

    @property
    def dedup_key(self) -> str:
        return f"{self.source}|{self.event_id}|{self.native_id or ''}"


@dataclass
class EventQueue:
    path: Path
    _seen: set[str] = field(default_factory=set, repr=False)

    def load(self) -> list[SourceEvent]:
        if not self.path.exists():
            return []
        events: list[SourceEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            events.append(SourceEvent(**row))
            self._seen.add(row["event_id"])
        return events

    def enqueue(self, event: SourceEvent) -> bool:
        """Return False if duplicate."""
        if event.dedup_key in self._seen or event.event_id in self._seen:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        self._seen.add(event.event_id)
        self._seen.add(event.dedup_key)
        return True

    def mark_processed(self, event_id: str, *, status: str = "processed") -> None:
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
                    )
                )
            else:
                updated.append(event)
        with self.path.open("w", encoding="utf-8") as handle:
            for event in updated:
                handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
