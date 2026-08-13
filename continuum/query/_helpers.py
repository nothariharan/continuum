from __future__ import annotations

from typing import Any

from continuum.hydradb import HydraDBClient


def one(client: HydraDBClient, query: str, parameters: dict[str, Any]) -> dict[str, Any] | None:
    rows = client.execute(query, parameters).rows
    return rows[0] if rows else None


def absent(entity_id: str, predicate: str) -> dict[str, Any]:
    return {
        "status": "ABSENT",
        "entity_id": entity_id,
        "predicate": predicate,
        "value": None,
        "evidence": [],
    }

