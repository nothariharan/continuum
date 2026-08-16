"""Canonical-entity persistence and query layer (Phase 3B).

Stores resolved CanonicalEntity objects as :Entity nodes in HydraDB with
their aliases (alias -> sources), emails, usernames, external ids, and
resolution provenance. The original mentions and claims are never deleted —
resolution adds canonical identity on top of source evidence.

Graph shape:

    (:Entity {key: person:soham, label: Person, name: ...})
        -[:HAS_ALIAS {source: slack}]-> ...
    (:Entity)-[:RESOLVED_FROM]->(mention metadata on the node)

    Claim (unchanged) -> ABOUT / predicate -> Entity (canonical)

Query layer:
    resolve_entity(mention)      mention -> canonical key
    get_entity_aliases(key)      all alias forms + their sources
    get_entity_sources(key)      source systems that mention the entity
    get_entity_evidence(key)     resolution provenance (why merged)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from continuum.hydradb import HydraDBClient

from .models import CanonicalEntity
from .pairs import IdentityPair

CREATE_ENTITY = """
UNWIND $rows AS row
MERGE (e {id: row.id})
SET e:Entity,
    e.key = row.key,
    e.label = row.label,
    e.name = row.name,
    e.aliases = row.aliases,
    e.alias_sources = row.alias_sources,
    e.emails = row.emails,
    e.usernames = row.usernames,
    e.external_ids = row.external_ids,
    e.sources = row.sources,
    e.provenance = row.provenance
"""

READ_ENTITY_BY_KEY = """
MATCH (e:Entity {key: $key})
RETURN e.key AS key, e.label AS label, e.name AS name,
       e.aliases AS aliases, e.alias_sources AS alias_sources,
       e.emails AS emails, e.usernames AS usernames,
       e.external_ids AS external_ids, e.sources AS sources,
       e.provenance AS provenance
"""

_ENTITY_RETURN = """
RETURN e.key AS key, e.label AS label, e.name AS name,
       e.aliases AS aliases, e.alias_sources AS alias_sources,
       e.emails AS emails, e.usernames AS usernames,
       e.external_ids AS external_ids, e.sources AS sources,
       e.provenance AS provenance
"""

READ_ENTITY_BY_ALIAS = (
    "MATCH (e:Entity) WHERE e.aliases STARTS WITH $mention\n" + _ENTITY_RETURN
)
READ_ENTITY_BY_USERNAME = (
    "MATCH (e:Entity) WHERE e.usernames STARTS WITH $mention\n" + _ENTITY_RETURN
)
READ_ENTITY_BY_EMAIL = (
    "MATCH (e:Entity) WHERE e.emails STARTS WITH $mention\n" + _ENTITY_RETURN
)

SCAN_ENTITIES = "MATCH (e:Entity)\n" + _ENTITY_RETURN

DELETE_ENTITIES = """
MATCH (e:Entity)
WHERE e.id >= $min_id AND e.id <= $max_id
DETACH DELETE e
"""

ENTITY_ID_OFFSET = 2_000_000_000_000
ENTITY_ID_SPAN = 100_000


def _pack_alias_sources(alias_sources: dict[str, set[str]]) -> str:
    return json.dumps({a: sorted(ss) for a, ss in alias_sources.items()}, ensure_ascii=False)


def _unpack_alias_sources(raw: str | None) -> dict[str, list[str]]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def entity_to_row(entity: CanonicalEntity, entity_id: int) -> dict[str, Any]:
    return {
        "id": entity_id,
        "key": entity.entity_key,
        "label": entity.label,
        "name": entity.name,
        "aliases": "|".join(sorted(entity.aliases)),
        "alias_sources": _pack_alias_sources(entity.alias_sources),
        "emails": "|".join(sorted(entity.emails)),
        "usernames": "|".join(sorted(entity.usernames)),
        "external_ids": "|".join(sorted(entity.external_ids)),
        "sources": "|".join(sorted(entity.sources)),
        "provenance": json.dumps(entity.resolution_provenance, ensure_ascii=False),
    }


def row_to_entity(row: dict[str, Any]) -> CanonicalEntity:
    aliases = {a for a in (row.get("aliases") or "").split("|") if a}
    entity = CanonicalEntity(
        entity_key=row["key"],
        label=row.get("label") or "Person",
        name=row.get("name") or row["key"],
        aliases=aliases,
        mentions=set(aliases),
        emails={e for e in (row.get("emails") or "").split("|") if e},
        usernames={u for u in (row.get("usernames") or "").split("|") if u},
        external_ids={e for e in (row.get("external_ids") or "").split("|") if e},
        sources={s for s in (row.get("sources") or "").split("|") if s},
        alias_sources={
            alias: set(sources)
            for alias, sources in _unpack_alias_sources(row.get("alias_sources")).items()
        },
        resolution_provenance=json.loads(row.get("provenance") or "[]") or [],
    )
    return entity


@dataclass
class EntityStore:
    """Persistence + query for canonical entities over HydraDB."""

    client: HydraDBClient

    # ---- writes ---------------------------------------------------------

    def save(self, entities: Iterable[CanonicalEntity], reset: bool = False) -> int:
        entity_list = list(entities)
        if reset:
            self._delete_all()
        rows = [
            entity_to_row(entity, ENTITY_ID_OFFSET + index)
            for index, entity in enumerate(entity_list)
        ]
        for index in range(0, len(rows), 50):
            self.client.execute_batch(CREATE_ENTITY, rows[index : index + 50])
        return len(rows)

    def _delete_all(self) -> None:
        step = 100
        for low in range(ENTITY_ID_OFFSET, ENTITY_ID_OFFSET + ENTITY_ID_SPAN, step):
            self.client.execute(
                DELETE_ENTITIES,
                {"min_id": low, "max_id": low + step - 1},
            )

    # ---- queries ---------------------------------------------------------

    def get_entity(self, entity_key: str) -> CanonicalEntity | None:
        rows = self.client.execute(READ_ENTITY_BY_KEY, {"key": entity_key}).rows
        return row_to_entity(rows[0]) if rows else None

    def resolve_mention(self, mention: str) -> dict[str, Any]:
        """Mention surface form -> canonical entity (or explicit absent).

        HydraDB supports only STARTS WITH / equality in WHERE (no CONTAINS,
        no list membership). The canonical entity table is small by design,
        so this scans the table once and enforces exact pipe-delimited
        membership client-side. O(#canonical_entities) per lookup.
        """
        rows = self.client.execute(SCAN_ENTITIES).rows
        for row in rows:
            fields = (
                (row.get("aliases") or "").split("|")
                + (row.get("usernames") or "").split("|")
                + (row.get("emails") or "").split("|")
            )
            if mention in fields:
                return {
                    "status": "definitive",
                    "mention": mention,
                    "entity_key": row["key"],
                    "value": {"entity_id": row["key"], "name": row["name"]},
                }
        return {
            "status": "absent",
            "mention": mention,
            "entity_key": None,
            "value": None,
        }

    def get_entity_aliases(self, entity_key: str) -> dict[str, Any]:
        entity = self.get_entity(entity_key)
        if entity is None:
            return {"status": "absent", "entity_key": entity_key, "aliases": []}
        return {
            "status": "definitive",
            "entity_key": entity_key,
            "aliases": sorted(entity.aliases),
            "alias_sources": entity.alias_sources_dict(),
        }

    def get_entity_sources(self, entity_key: str) -> dict[str, Any]:
        entity = self.get_entity(entity_key)
        if entity is None:
            return {"status": "absent", "entity_key": entity_key, "sources": []}
        return {
            "status": "definitive",
            "entity_key": entity_key,
            "sources": sorted(entity.sources),
            "emails": sorted(entity.emails),
            "usernames": sorted(entity.usernames),
            "external_ids": sorted(entity.external_ids),
        }

    def get_entity_evidence(self, entity_key: str) -> dict[str, Any]:
        entity = self.get_entity(entity_key)
        if entity is None:
            return {"status": "absent", "entity_key": entity_key, "evidence": []}
        return {
            "status": "definitive",
            "entity_key": entity_key,
            "evidence": entity.resolution_provenance,
            "members": sorted(entity.members),
        }


def build_store(client: HydraDBClient) -> EntityStore:
    return EntityStore(client)
