"""Shared Mention and Claim schemas for Phase 2B extraction contract v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

SUPPORTED_PREDICATES = frozenset(
    {"OWNS", "LEADS", "ASSIGNED_TO", "BLOCKS", "DEPENDS_ON", "REVIEWS"}
)
MENTION_TYPES = frozenset(
    {"person", "project", "account", "ticket", "email", "username", "org"}
)
EXTRACTION_METHODS = frozenset({"deterministic", "llm", "hybrid"})


def _stable_hash(*parts: str) -> str:
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
        mention_id = _stable_hash(artifact_id, raw_text, type, str(span_start))
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
        claim_id = _stable_hash(
            artifact_id, subject_mention, predicate, object_mention
        )
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


@dataclass(frozen=True)
class GroundTruthRecord:
    artifact_id: str
    mentions: list[dict]
    claims: list[dict]
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def mention_to_dict(mention: Mention) -> dict:
    return asdict(mention)


def claim_to_dict(claim: Claim) -> dict:
    return asdict(claim)


def mention_from_dict(data: dict) -> Mention:
    return Mention(**data)


def claim_from_dict(data: dict) -> Claim:
    return Claim(**data)


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_artifacts_jsonl(path: Path) -> list[dict]:
    return list(read_jsonl(path))


def artifacts_from_dicts(rows: list[dict]):
    from continuum.dataset.artifact import Artifact

    return [
        Artifact(
            id=row["id"],
            source=row["source"],
            source_id=row["source_id"],
            type=row["type"],
            author=row.get("author"),
            timestamp=row.get("timestamp"),
            title=row.get("title"),
            content=row["content"],
            metadata=row.get("metadata") or {},
        )
        for row in rows
    ]
