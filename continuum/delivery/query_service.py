"""Thin query service — delegates to continuum.benchmark.answer()."""

from __future__ import annotations

from typing import Any

from continuum.benchmark import answer
from continuum.benchmark.contract import validate_result
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient


class QueryService:
    """Transport-agnostic query seam for Slack bot, MCP, and future Web UI.

    When no ``entity_store`` is injected, the persisted canonical entities
    (``:Entity`` nodes written by the extraction/ingestion path) are restored
    from HydraDB so ad-hoc questions resolve mentions exactly like the
    validated source→answer vertical.
    """

    def __init__(self, client: HydraDBClient, *, entity_store=None) -> None:
        self._client = client
        self._entity_store = entity_store or EntityStore(client)

    def ask(self, question_text: str, *, question_id: str = "ad-hoc") -> dict[str, Any]:
        payload = {
            "question_id": question_id,
            "question": question_text,
        }
        result = answer(self._client, payload, entity_store=self._entity_store)
        validate_result(result)
        return result

    def health(self) -> dict[str, Any]:
        self._client.health_check()
        return {"status": "ok", "database": getattr(self._client, "database", "hydradb")}
