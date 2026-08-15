"""Shared data contract for Phase 2B and beyond.

This module defines the machine-readable structures the extraction pipeline
(teammate) produces and the graph/state pipeline (founder) consumes:

- Mention: an entity reference inside an artifact (intentionally unresolved).
- Claim: an atomic evidence-derived statement built from mentions.

The Artifact contract lives in `continuum/dataset/artifact.py`; claims
reference artifacts by `artifact_id` (either a fixture key or a normalized
`dsid_<32-hex>` id).

This contract is team-owned. Do not change it without explicit agreement.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime

CLAIM_ID_RE = re.compile(r"^claim:[A-Za-z0-9_-]+$")
MENTION_ID_RE = re.compile(r"^mention:[A-Za-z0-9_-]+$")
ARTIFACT_ID_RE = re.compile(r"^(dsid_[0-9a-f]{32}|artifact:[A-Za-z0-9_-]+)$")
PREDICATE_RE = re.compile(r"^[A-Z][A-Z_]+$")
MENTION_TYPE_RE = re.compile(r"^[A-Z][A-Z_]+$")

ISO_TS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9:]{2}(?::[0-9]{2})?(?:Z|[+-][0-9]{2}:?[0-9]{2})?)?$")

OPEN_END = "9999-12-31"

VALID_MENTION_TYPES = {"PERSON", "ORG", "PROJECT", "ACCOUNT", "SERVICE", "REPO", "TEAM", "PRODUCT", "OTHER"}


@dataclass(frozen=True)
class Mention:
    mention_id: str
    artifact_id: str
    text: str
    mention_type: str
    span_start: int | None = None
    span_end: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    artifact_id: str
    subject_mention: str
    predicate: str
    object_mention: str
    observed_at: str
    valid_from: str
    valid_to: str | None
    confidence: float
    extraction_method: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_iso(value: str) -> str:
    """Canonicalize an ISO date/datetime to 'YYYY-MM-DD' for graph keys."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return value[:10]
