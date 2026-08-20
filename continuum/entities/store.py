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
    _cached_entities: list[CanonicalEntity] | None = field(default=None, init=False, repr=False)
    _cached_index: Any | None = field(default=None, init=False, repr=False)
    _inventory_by_key: dict[str, dict] | None = field(default=None, init=False, repr=False)

    def _load_inventory_index(self) -> dict[str, dict]:
        if self._inventory_by_key is not None:
            return self._inventory_by_key
        from pathlib import Path

        from .candidates import normalize_company_name, normalize_slug

        path = Path(__file__).resolve().parents[2] / "data" / "extraction" / "mention_inventory.json"
        index: dict[str, dict] = {}
        try:
            inventory = json.loads(path.read_text(encoding="utf-8"))
            for entry in inventory["entries"]:
                keys = {
                    entry.get("raw_mention", ""),
                    entry.get("normalized", ""),
                }
                for alias in entry.get("aliases") or ():
                    keys.add(alias)
                for key in keys:
                    if not key:
                        continue
                    index[key] = entry
                    index[key.lower()] = entry
                    slug = normalize_slug(key)
                    if slug:
                        index[slug] = entry
                    company_slug = normalize_company_name(key)
                    if company_slug:
                        index[company_slug] = entry
        except (OSError, json.JSONDecodeError, KeyError):
            index = {}
        self._inventory_by_key = index
        return index

    def _inventory_entry(self, mention: str) -> dict:
        from .candidates import normalize_company_name, normalize_slug

        index = self._load_inventory_index()
        if mention in index:
            return index[mention]
        lower = mention.lower()
        if lower in index:
            return index[lower]
        slug = normalize_slug(mention)
        if slug and slug in index:
            return index[slug]
        company_slug = normalize_company_name(mention)
        if company_slug and company_slug in index:
            return index[company_slug]
        return {}

    def _load_entities(self) -> list[CanonicalEntity]:
        if self._cached_entities is None:
            rows = self.client.execute(SCAN_ENTITIES).rows
            self._cached_entities = [row_to_entity(row) for row in rows]
        return self._cached_entities

    def _candidate_index(self):
        if self._cached_index is None:
            from .candidates import CandidateIndex

            self._cached_index = CandidateIndex.build(self._load_entities())
        return self._cached_index

    def _match_entity_slug(self, mention: str, entity: CanonicalEntity) -> bool:
        from .candidates import normalize_company_name, normalize_slug

        slug = normalize_slug(mention)
        company_slug = normalize_company_name(mention)
        if not slug and not company_slug:
            return False
        for form in self._surface_forms(entity):
            if slug and normalize_slug(form) == slug:
                return True
            if company_slug and normalize_company_name(form) == company_slug:
                return True
        return False

    def _surface_forms(self, entity: CanonicalEntity) -> set[str]:
        return set(entity.aliases) | set(entity.emails) | set(entity.usernames) | {entity.name}

    def _match_entity_exact(self, mention: str, entity: CanonicalEntity) -> bool:
        if mention in self._surface_forms(entity):
            return True
        lower = mention.lower()
        return any(form.lower() == lower for form in self._surface_forms(entity))

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
        self._cached_entities = None
        self._cached_index = None
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
        """Mention surface form -> canonical entity (or explicit absent)."""
        from .candidates import candidate_from_mention, signals_from_mention

        mention = mention.strip()
        if not mention:
            return {"status": "absent", "mention": mention, "entity_key": None, "value": None}

        entities = self._load_entities()
        for entity in entities:
            if self._match_entity_exact(mention, entity):
                return {
                    "status": "definitive",
                    "mention": mention,
                    "entity_key": entity.entity_key,
                    "value": {"entity_id": entity.entity_key, "name": entity.name},
                }

        slug_matches = [entity for entity in entities if self._match_entity_slug(mention, entity)]
        if len(slug_matches) == 1:
            entity = slug_matches[0]
            return {
                "status": "definitive",
                "mention": mention,
                "entity_key": entity.entity_key,
                "value": {"entity_id": entity.entity_key, "name": entity.name},
            }

        inventory = self._inventory_entry(mention)
        signals = signals_from_mention(mention, inventory_entry=inventory)
        candidate = candidate_from_mention(
            mention,
            type=signals.type,
            emails=signals.emails,
            usernames=signals.usernames,
            external_ids=signals.external_ids,
            source=signals.source,
        )
        ranked = self._candidate_index().lookup(candidate.signals, limit=5)
        if not ranked:
            return {"status": "absent", "mention": mention, "entity_key": None, "value": None}

        top_key, top_hits = ranked[0]
        if len(ranked) > 1 and ranked[1][1] == top_hits:
            return {"status": "absent", "mention": mention, "entity_key": None, "value": None}

        from .candidates import normalize_company_name, normalize_slug

        mention_slug = normalize_slug(mention)
        company_slug = normalize_company_name(mention)
        slug_keys = set()
        if mention_slug:
            slug_keys.update(self._candidate_index().by_slug.get(mention_slug, ()))
        if company_slug:
            slug_keys.update(self._candidate_index().by_company_slug.get(company_slug, ()))

        strong_signal = top_hits >= 2 or (
            top_hits == 1
            and (
                "@" in mention
                or mention.startswith("@")
                or any(ext in mention for ext in signals.external_ids)
                or (len(slug_keys) == 1 and top_key in slug_keys)
            )
        )
        if not strong_signal:
            return {"status": "absent", "mention": mention, "entity_key": None, "value": None}

        entity = next((e for e in entities if e.entity_key == top_key), None)
        if entity is None:
            return {"status": "absent", "mention": mention, "entity_key": None, "value": None}
        return {
            "status": "definitive",
            "mention": mention,
            "entity_key": entity.entity_key,
            "value": {"entity_id": entity.entity_key, "name": entity.name},
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
