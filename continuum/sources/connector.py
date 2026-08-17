"""Source connector protocol — fetch upstream records, normalize to Artifact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from continuum.dataset.artifact import Artifact

from .cursor import SyncCursor


@dataclass(frozen=True)
class FetchResult:
    records: list[Any]
    next_cursor: SyncCursor | None


class SourceConnector(Protocol):
    """Contract for live or fixture-backed source ingestion."""

    source: str

    def authenticate(self) -> None:
        """Validate credentials or fixture configuration."""
        ...

    def fetch(self, *, cursor: SyncCursor | None = None, limit: int = 100) -> FetchResult:
        """Return raw upstream records and an optional next cursor."""
        ...

    def normalize(self, raw: Any) -> Artifact:
        """Map one upstream record to the canonical Artifact."""
        ...

    def cursor(self, raw: Any) -> SyncCursor:
        """Derive sync cursor from the latest raw record."""
        ...

    def provenance(self, raw: Any) -> dict[str, Any]:
        """Source-specific provenance metadata (stored in Artifact.metadata)."""
        ...
