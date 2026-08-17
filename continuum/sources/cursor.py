"""Incremental sync cursor for source connectors."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SyncCursor:
    """Opaque per-source sync position."""

    source: str
    value: str
    last_sync_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncCursor:
        return cls(
            source=str(data["source"]),
            value=str(data["value"]),
            last_sync_at=data.get("last_sync_at"),
        )
