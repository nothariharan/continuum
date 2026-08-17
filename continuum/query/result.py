"""Canonical state-result envelope.

Every query in `continuum.query` returns this same structured shape so that
current state, historical state, provenance, conflict, and abstention are
interchangeable for callers — this is the eventual MCP / API / UI contract.

Envelope:

{
  "entity_id": "account:acme",          # canonical entity key queried
  "predicate": "OWNS",
  "status": "definitive",               # definitive | absent | conflict | consistent
  "value": {"entity_id": ..., "name": ...} | None,
  "valid_from": "2026-07-28" | None,
  "valid_to": "9999-12-31" | None,
  "confidence": 0.94 | None,
  "as_of": "2026-07-15" | None,         # set by historical queries only
  "conflicting_subjects": ["person:a", ...],  # conflict queries only
  "claims": [ ... ],                    # conflict queries only (full claim rows)
  "evidence": [                         # provenance queries only
    {
      "claim_id": "claim:123",
      "subject_mention": "Sarah",
      "object_mention": "Acme",
      "artifact_id": "dsid_...",
      "artifact_kind": "gmail_message",
      "source_id": "source:gmail",
      "source": "Gmail",
      "observed_at": "2026-07-28"
    }
  ]
}

Unknown/not-applicable fields are always present with null/empty values.
"""

from __future__ import annotations

from typing import Any

ENVELOPE_KEYS = frozenset(
    {
        "entity_id",
        "predicate",
        "status",
        "value",
        "valid_from",
        "valid_to",
        "confidence",
        "as_of",
        "conflicting_subjects",
        "claims",
        "evidence",
        "history",
        "resolution",
    }
)


def result(
    entity_id: str,
    predicate: str,
    status: str,
    value: dict[str, Any] | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    confidence: float | None = None,
    as_of: str | None = None,
    conflicting_subjects: list[str] | None = None,
    claims: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
    resolution: str | None = None,
) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "predicate": predicate,
        "status": status,
        "value": value,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "confidence": confidence,
        "as_of": as_of,
        "conflicting_subjects": conflicting_subjects or [],
        "claims": claims or [],
        "evidence": evidence or [],
        "history": history or [],
        "resolution": resolution,
    }


def absent(entity_id: str, predicate: str) -> dict[str, Any]:
    """Canonical abstention: no claim supports an answer, so no guess."""
    return result(entity_id, predicate, "absent")


def evidence_item(
    claim_id: str,
    subject_mention: str,
    object_mention: str,
    artifact_id: str | None,
    artifact_kind: str | None,
    source_id: str | None,
    source: str | None,
    observed_at: str | None,
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "subject_mention": subject_mention,
        "object_mention": object_mention,
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "source_id": source_id,
        "source": source,
        "observed_at": observed_at,
    }
