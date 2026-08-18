"""Thin query service — delegates to continuum.benchmark.answer()."""

from __future__ import annotations

from typing import Any

from continuum.benchmark import answer
from continuum.benchmark.contract import validate_result
from continuum.hydradb import HydraDBClient


class QueryService:
    """Transport-agnostic query seam for Slack bot, MCP, and future Web UI."""

    def __init__(self, client: HydraDBClient, *, entity_store=None) -> None:
        self._client = client
        self._entity_store = entity_store

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
        return {"status": "ok", "database": self._client.database}
