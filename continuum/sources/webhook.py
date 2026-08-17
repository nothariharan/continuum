"""Webhook/event ingestion interface stub — production wiring is future work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from continuum.dataset.artifact import Artifact


@dataclass(frozen=True)
class SourceEvent:
    """Normalized upstream event before adapter normalization."""

    source: str
    event_type: str
    payload: dict[str, Any]
    received_at: str


class WebhookHandler(Protocol):
    """Future: Slack events API, Gmail push notifications, GitHub webhooks."""

    source: str

    def verify(self, headers: dict[str, str], body: bytes) -> bool:
        """Validate webhook signature."""
        ...

    def parse(self, body: bytes) -> SourceEvent:
        """Parse raw webhook body into a SourceEvent."""
        ...

    def to_artifact(self, event: SourceEvent) -> Artifact:
        """Delegate to the source adapter normalize path."""
        ...
