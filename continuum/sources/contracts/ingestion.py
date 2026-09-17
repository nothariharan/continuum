"""Ingestion job lifecycle (UI telemetry and worker state machine)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IngestionJobStatus(StrEnum):
    QUEUED = "queued"
    DISCOVERING_CHANNELS = "discovering_channels"
    BACKFILLING_MESSAGES = "backfilling_messages"
    EXTRACTING_GRAPH_STATE = "extracting_graph_state"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class IngestionJobProgress:
    job_id: str
    tenant_id: str
    workspace_id: str
    source: str
    status: IngestionJobStatus
    messages_processed: int = 0
    messages_total: int | None = None
    error_message: str | None = None

    @property
    def fraction_complete(self) -> float | None:
        if self.messages_total is None or self.messages_total <= 0:
            return None
        return min(1.0, self.messages_processed / self.messages_total)
