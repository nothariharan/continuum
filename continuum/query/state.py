"""Generalized state/provenance queries over the Phase 1 graph shape.

Same semantics as the Phase 1 query functions (current_state.py, history.py,
conflicts.py, provenance.py) but predicate-parameterized so real claim data
with OWNS / MAINTAINS / REVIEWS / DEPENDS_ON can be resolved without new
query code per predicate.

Rel types are interpolated from a fixed allowlist (HydraDB cannot
parameterize relationship types), identical to how Phase 1 hard-codes them.

Phase 1 functions are untouched; these are the Phase 2B generalizations.
"""

from __future__ import annotations

from typing import Any

from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import PREDICATE_RELS
from ._helpers import absent, one

OPEN_END = "9999-12-31"

CURRENT_STATE = """
MATCH (s)-[r:{rel}]->(o {{key: $entity_key}})
WHERE r.valid_to = $open_end
RETURN s.key AS subject_id, s.name AS subject_name, r.valid_from AS valid_from
ORDER BY r.valid_from DESC LIMIT 1
"""

STATE_ON = """
MATCH (s)-[r:{rel}]->(o {{key: $entity_key}})
WHERE r.valid_from <= $date AND r.valid_to > $date
RETURN s.key AS subject_id, s.name AS subject_name,
       r.valid_from AS valid_from, r.valid_to AS valid_to
ORDER BY r.valid_from DESC LIMIT 1
"""

CONFLICTS = """
MATCH (c:Claim)-[:ABOUT]->(o {key: $entity_key})
WHERE c.object_id = $entity_key AND c.predicate = $predicate
RETURN c.key AS claim_id, c.subject_id AS subject_id,
       c.subject_name AS subject_name, c.subject_mention AS subject_mention,
       c.object_mention AS object_mention,
       c.observed_at AS observed_at, c.valid_from AS valid_from, c.valid_to AS valid_to
ORDER BY c.observed_at
"""

PROVENANCE = """
MATCH (c:Claim {object_id: $entity_key})-[:ABOUT]->(o {key: $entity_key}),
      (c)-[:SOURCED_FROM]->(artifact:Artifact)-[:FROM]->(source:Source)
WHERE c.predicate = $predicate
RETURN c.subject_id AS subject_id, c.subject_name AS subject_name,
       c.key AS claim_id, c.subject_mention AS subject_mention,
       c.object_mention AS object_mention,
       artifact.key AS artifact_id, artifact.dsid AS artifact_dsid,
       artifact.kind AS artifact_kind, artifact.type AS artifact_type,
       artifact.observed_at AS observed_at, artifact.timestamp AS artifact_timestamp,
       source.key AS source_id, source.name AS source_name
ORDER BY observed_at
"""


def _rel(predicate: str) -> str:
    if predicate not in PREDICATE_RELS:
        raise ValueError(f"unsupported predicate: {predicate!r}; allowed: {PREDICATE_RELS}")
    return predicate


def resolve_state(client: HydraDBClient, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
    """Current resolved state: latest open-validity subject for (entity, predicate)."""
    row = one(
        client,
        CURRENT_STATE.format(rel=_rel(predicate)),
        {"entity_key": entity_key, "open_end": OPEN_END},
    )
    if not row:
        return absent(entity_key, predicate)
    return {
        "status": "definitive",
        "entity_id": entity_key,
        "predicate": predicate,
        "value": {"entity_id": row["subject_id"], "name": row["subject_name"]},
        "valid_from": row["valid_from"],
        "valid_to": None,
        "confidence": 0.96,
        "evidence": [],
    }


def resolve_state_on(
    client: HydraDBClient, entity_key: str, date: str, predicate: str = "OWNS"
) -> dict[str, Any]:
    """State as of a date, from the validity intervals on the resolved relationship."""
    row = one(
        client,
        STATE_ON.format(rel=_rel(predicate)),
        {"entity_key": entity_key, "date": date},
    )
    if not row:
        return absent(entity_key, predicate)
    return {
        "status": "definitive",
        "entity_id": entity_key,
        "predicate": predicate,
        "as_of": date,
        "value": {"entity_id": row["subject_id"], "name": row["subject_name"]},
        "valid_from": row["valid_from"],
        "valid_to": row["valid_to"],
        "confidence": 0.96,
        "evidence": [],
    }


def resolve_conflicts(client: HydraDBClient, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
    """All claims about (entity, predicate); CONFLICT if multiple subjects."""
    rows = client.execute(
        CONFLICTS,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    subjects = sorted({row["subject_id"] for row in rows})
    return {
        "status": "CONFLICT" if len(subjects) > 1 else "CONSISTENT",
        "entity_id": entity_key,
        "predicate": predicate,
        "conflicting_subjects": subjects,
        "claims": rows,
    }


def resolve_provenance(client: HydraDBClient, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
    """Evidence chain: Claim -> SOURCED_FROM -> Artifact -> FROM -> Source."""
    rows = client.execute(
        PROVENANCE,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    if not rows:
        return absent(entity_key, predicate)
    return {
        "status": "definitive",
        "entity_id": entity_key,
        "predicate": predicate,
        "value": {"entity_id": rows[-1]["subject_id"], "name": rows[-1]["subject_name"]},
        "evidence": [
            {
                "claim_id": row["claim_id"],
                "subject_mention": row["subject_mention"],
                "object_mention": row["object_mention"],
                "artifact_id": row["artifact_id"] or row["artifact_dsid"],
                "artifact_kind": row["artifact_kind"] or row["artifact_type"],
                "source_id": row["source_id"],
                "source": row["source_name"],
                "observed_at": row["observed_at"] or row["artifact_timestamp"],
            }
            for row in rows
        ],
    }
