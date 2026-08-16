"""Semantic state interface — the future public API surface (Y10).

These are the operations Continuum will eventually expose through MCP / REST /
web. THIS MODULE ONLY DEFINES THE CONTRACT — it is not wired to MCP yet
(Phase 6) and must not drift from the stable query layer.

Every function returns the canonical result envelope from
`continuum.query.result`, so any future transport (MCP tool, HTTP endpoint)
is a thin adapter over these functions — never a second implementation of
the state logic.

The entity-resolution bridge (Phase 3) plugs in front: a user question
mentions a surface form; resolve_entity maps it to a canonical entity key
before these queries run.

Contract rules:
- entity_key is a canonical key (account:acme-health, person:may-patel)
- predicate is one of SUPPORTED_PREDICATES (default OWNS)
- dates are ISO YYYY-MM-DD
- abstention is explicit: absent status, never a guessed value
"""

from __future__ import annotations

from typing import Any, Protocol

from continuum.hydradb import HydraDBClient
from continuum.query import (
    resolve_conflicts,
    resolve_provenance,
    resolve_state,
    resolve_state_on,
)
from continuum.query.result import absent

HISTORY_QUERY = """
MATCH (s)-[r:{rel}]->(o {{key: $entity_key}})
RETURN s.key AS subject_id, s.name AS subject_name,
       r.valid_from AS valid_from, r.valid_to AS valid_to
ORDER BY r.valid_from
"""

DEPENDENCIES_QUERY = """
MATCH (o {key: $entity_key})-[:DEPENDS_ON]->(d)
RETURN d.key AS dependency_key, d.name AS dependency_name
ORDER BY d.key
"""


class SemanticQuery(Protocol):
    """The stable interface every transport will wrap (Y10 contract)."""

    def resolve_entity(self, mention: str) -> dict[str, Any]:
        """Map a surface mention to a canonical entity key (Phase 3 bridge)."""

    def get_current_state(self, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
        """Current resolved state for (entity, predicate)."""

    def get_state_as_of(self, entity_key: str, date: str, predicate: str = "OWNS") -> dict[str, Any]:
        """Resolved state at a point in time."""

    def get_history(self, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
        """Ordered history of resolved state transitions."""

    def get_conflicts(self, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
        """Conflicting claims about (entity, predicate)."""

    def get_evidence(self, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
        """Provenance chain: claims -> artifacts -> sources."""

    def get_dependencies(self, entity_key: str) -> dict[str, Any]:
        """Graph dependencies (future: DEPENDS_ON/BLOCKS traversal in HydraDB)."""


class StateQueryAdapter:
    """Default implementation over the stable query layer.

    Deliberately thin: each method delegates to the existing resolvers and
    returns their canonical envelope unchanged. Entity resolution is injected
    (Phase 3); until then mention strings must already be canonical keys.
    """

    def __init__(self, client: HydraDBClient, entity_store=None) -> None:
        self._client = client
        self._entity_store = entity_store

    def resolve_entity(self, mention: str) -> dict[str, Any]:
        if self._entity_store is None:
            # Phase 3 store not wired: treat the mention as a canonical key.
            return {"status": "definitive", "entity_key": mention, "resolver": "passthrough"}
        return self._entity_store.resolve_mention(mention)

    def get_entity_aliases(self, entity_key: str) -> dict[str, Any]:
        if self._entity_store is None:
            return {"status": "absent", "entity_key": entity_key, "aliases": []}
        return self._entity_store.get_entity_aliases(entity_key)

    def get_entity_sources(self, entity_key: str) -> dict[str, Any]:
        if self._entity_store is None:
            return {"status": "absent", "entity_key": entity_key, "sources": []}
        return self._entity_store.get_entity_sources(entity_key)

    def get_entity_evidence(self, entity_key: str) -> dict[str, Any]:
        if self._entity_store is None:
            return {"status": "absent", "entity_key": entity_key, "evidence": []}
        return self._entity_store.get_entity_evidence(entity_key)

    def get_current_state(self, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
        return resolve_state(self._client, entity_key, predicate)

    def get_state_as_of(self, entity_key: str, date: str, predicate: str = "OWNS") -> dict[str, Any]:
        return resolve_state_on(self._client, entity_key, date, predicate)

    def get_history(self, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
        rows = self._client.execute(
            HISTORY_QUERY.format(rel=predicate),
            {"entity_key": entity_key},
        ).rows
        if not rows:
            return absent(entity_key, predicate)
        return {
            "entity_id": entity_key,
            "predicate": predicate,
            "status": "definitive",
            "history": rows,
        }

    def get_conflicts(self, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
        return resolve_conflicts(self._client, entity_key, predicate)

    def get_evidence(self, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
        return resolve_provenance(self._client, entity_key, predicate)

    def get_dependencies(self, entity_key: str) -> dict[str, Any]:
        rows = self._client.execute(
            DEPENDENCIES_QUERY,
            {"entity_key": entity_key},
        ).rows
        return {
            "entity_id": entity_key,
            "predicate": "DEPENDS_ON",
            "status": "definitive" if rows else "absent",
            "dependencies": rows,
        }


__all__ = ["SemanticQuery", "StateQueryAdapter"]
