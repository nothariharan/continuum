"""Shared data contract — Phase 2B contract v1 (LOCKED at Gate 1 sign-off).

This module is the single canonical implementation of the Artifact/Mention/
Claim contract. `continuum/extract/schemas.py` re-exports from here so the
extraction pipeline and the graph pipeline share one definition.

Artifact is defined in `continuum/dataset/artifact.py` (unchanged since
Phase 2A); claims reference artifacts by `artifact_id` (dsid_<32-hex> for
real data, or artifact:<key> for fixtures).

Contract v1 semantics (docs/contract-v1.md):
- extraction outputs raw mentions, never canonical entity IDs
- timestamps are nullable when not stated; the graph side maps
  open-ended `valid_to: null` to the sentinel 9999-12-31
- every claim carries `evidence_span` (verbatim quote) and
  `extraction_method`
- stable ids are 16-hex sha256 hashes (or claim:<slug> for hand-written
  fixtures)

Team-owned: changes require explicit agreement.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime

CLAIM_ID_RE = re.compile(r"^(claim:[A-Za-z0-9_-]+|[0-9a-f]{16})$")
MENTION_ID_RE = re.compile(r"^(mention:[A-Za-z0-9_-]+|[0-9a-f]{16})$")
ARTIFACT_ID_RE = re.compile(r"^(dsid_[0-9a-f]{32}|artifact:[A-Za-z0-9_-]+)$")
PREDICATE_RE = re.compile(r"^[A-Z][A-Z_]+$")
MENTION_TYPE_RE = re.compile(r"^[a-z][a-z_]+$")

ISO_TS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9]{2}:[0-9]{2}(?::[0-9]{2})?(?:Z|[+-][0-9]{2}:?[0-9]{2})?)?$")

OPEN_END = "9999-12-31"

SUPPORTED_PREDICATES = frozenset(
    {"OWNS", "MAINTAINS", "LEADS", "ASSIGNED_TO", "BLOCKS", "DEPENDS_ON", "REVIEWS"}
)
SUPPORTED_MENTION_TYPES = frozenset(
    {"person", "project", "account", "ticket", "email", "username", "org"}
)
EXTRACTION_METHODS = frozenset({"deterministic", "llm", "hybrid", "hand-written"})


def stable_hash(*parts: str) -> str:
    """16-hex sha256 over | separated parts — the contract's id scheme."""
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_mention_text(text: str) -> str:
    value = text.strip()
    if value.startswith("@"):
        value = value[1:]
    return " ".join(value.lower().split())


@dataclass(frozen=True)
class Mention:
    mention_id: str
    artifact_id: str
    source: str
    raw_text: str
    type: str
    context: str
    source_identity: str | None
    span_start: int
    span_end: int
    extraction_method: str
    confidence: float

    @classmethod
    def create(
        cls,
        *,
        artifact_id: str,
        source: str,
        raw_text: str,
        type: str,
        content: str,
        span_start: int,
        span_end: int,
        source_identity: str | None = None,
        extraction_method: str = "deterministic",
        confidence: float = 0.85,
        context_radius: int = 120,
    ) -> "Mention":
        start = max(0, span_start - context_radius)
        end = min(len(content), span_end + context_radius)
        context = content[start:end].strip()
        mention_id = stable_hash(artifact_id, raw_text, type, str(span_start))
        return cls(
            mention_id=mention_id,
            artifact_id=artifact_id,
            source=source,
            raw_text=raw_text,
            type=type,
            context=context,
            source_identity=source_identity,
            span_start=span_start,
            span_end=span_end,
            extraction_method=extraction_method,
            confidence=confidence,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    artifact_id: str
    subject_mention: str
    predicate: str
    object_mention: str
    observed_at: str | None
    valid_from: str | None
    valid_to: str | None
    confidence: float
    extraction_method: str
    evidence_span: str
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        artifact_id: str,
        subject_mention: str,
        predicate: str,
        object_mention: str,
        observed_at: str | None,
        evidence_span: str,
        valid_from: str | None = None,
        valid_to: str | None = None,
        confidence: float = 0.85,
        extraction_method: str = "deterministic",
        metadata: dict | None = None,
    ) -> "Claim":
        if predicate not in SUPPORTED_PREDICATES:
            raise ValueError(f"unsupported predicate: {predicate}")
        claim_id = stable_hash(artifact_id, subject_mention, predicate, object_mention)
        return cls(
            claim_id=claim_id,
            artifact_id=artifact_id,
            subject_mention=subject_mention,
            predicate=predicate,
            object_mention=object_mention,
            observed_at=observed_at,
            valid_from=valid_from,
            valid_to=valid_to,
            confidence=confidence,
            extraction_method=extraction_method,
            evidence_span=evidence_span,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict:
        return asdict(self)


def parse_iso(value: str) -> str:
    """Canonicalize an ISO date/datetime to 'YYYY-MM-DD' for graph keys."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return value[:10]
