"""Generalized state/provenance queries over the Phase 1 graph shape.

Same semantics as the Phase 1 query functions (current_state.py, history.py,
conflicts.py, provenance.py) but predicate-parameterized so real claim data
with OWNS / MAINTAINS / LEADS / ASSIGNED_TO / BLOCKS / DEPENDS_ON / REVIEWS
can be resolved without new query code per predicate.

Every function returns the canonical envelope from `.result` — one shape for
current state, historical state, conflicts, provenance, and abstention.

Rel types are interpolated from a fixed allowlist (HydraDB cannot
parameterize relationship types), identical to how Phase 1 hard-codes them.
"""

from __future__ import annotations

from typing import Any

from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import PREDICATE_RELS
from ._helpers import one
from .result import absent, evidence_item, result

OPEN_END = "9999-12-31"

CURRENT_STATE = """
MATCH (c:Claim {object_id: $entity_key, predicate: $predicate})
WHERE c.valid_to = $open_end
RETURN c.subject_id AS subject_id, c.subject_name AS subject_name,
       c.valid_from AS valid_from
ORDER BY c.valid_from DESC LIMIT 1
"""

STATE_ON = """
MATCH (c:Claim {object_id: $entity_key, predicate: $predicate})
WHERE c.valid_from <= $date AND c.valid_to > $date
RETURN c.subject_id AS subject_id, c.subject_name AS subject_name,
       c.valid_from AS valid_from, c.valid_to AS valid_to
ORDER BY c.valid_from DESC LIMIT 1
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


def _subject_value(row: dict[str, Any]) -> dict[str, Any]:
    return {"entity_id": row["subject_id"], "name": row["subject_name"]}


def resolve_state(client: HydraDBClient, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
    """Current resolved state: latest open-validity subject for (entity, predicate)."""
    row = one(
        client,
        CURRENT_STATE,
        {"entity_key": entity_key, "predicate": _rel(predicate), "open_end": OPEN_END},
    )
    if not row:
        return absent(entity_key, predicate)
    return result(
        entity_id=entity_key,
        predicate=predicate,
        status="definitive",
        value=_subject_value(row),
        valid_from=row["valid_from"],
        valid_to=None,
        confidence=0.96,
    )


def resolve_state_on(
    client: HydraDBClient, entity_key: str, date: str, predicate: str = "OWNS"
) -> dict[str, Any]:
    """State as of a date, from the claim validity intervals."""
    row = one(
        client,
        STATE_ON,
        {"entity_key": entity_key, "predicate": _rel(predicate), "date": date},
    )
    if not row:
        return absent(entity_key, predicate)
    return result(
        entity_id=entity_key,
        predicate=predicate,
        status="definitive",
        value=_subject_value(row),
        valid_from=row["valid_from"],
        valid_to=row["valid_to"],
        confidence=0.96,
        as_of=date,
    )


def resolve_conflicts(client: HydraDBClient, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
    """All claims about (entity, predicate); status 'conflict' if multiple subjects."""
    rows = client.execute(
        CONFLICTS,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    subjects = sorted({row["subject_id"] for row in rows})
    return result(
        entity_id=entity_key,
        predicate=predicate,
        status="conflict" if len(subjects) > 1 else "consistent",
        conflicting_subjects=subjects,
        claims=rows,
    )


def resolve_provenance(client: HydraDBClient, entity_key: str, predicate: str = "OWNS") -> dict[str, Any]:
    """Evidence chain: Claim -> SOURCED_FROM -> Artifact -> FROM -> Source."""
    rows = client.execute(
        PROVENANCE,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    if not rows:
        return absent(entity_key, predicate)
    evidence = [
        evidence_item(
            claim_id=row["claim_id"],
            subject_mention=row["subject_mention"],
            object_mention=row["object_mention"],
            artifact_id=row["artifact_id"] or row["artifact_dsid"],
            artifact_kind=row["artifact_kind"] or row["artifact_type"],
            source_id=row["source_id"],
            source=row["source_name"],
            observed_at=row["observed_at"] or row["artifact_timestamp"],
        )
        for row in rows
    ]
    return result(
        entity_id=entity_key,
        predicate=predicate,
        status="definitive",
        value=_subject_value(rows[-1]),
        evidence=evidence,
    )
