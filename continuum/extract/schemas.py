"""Contract v1 schemas — canonical definition lives in `continuum.claims.schema`.

This module re-exports the shared Mention/Claim contract so the extraction
pipeline keeps the same public API while the graph pipeline and extraction
pipeline share one definition. Do not duplicate dataclasses here.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

from continuum.claims.schema import (
    EXTRACTION_METHODS,
    SUPPORTED_MENTION_TYPES as MENTION_TYPES,
    SUPPORTED_PREDICATES,
    Claim,
    Mention,
    normalize_mention_text,
    stable_hash as _stable_hash,
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


__all__ = [
    "EXTRACTION_METHODS",
    "MENTION_TYPES",
    "SUPPORTED_PREDICATES",
    "Claim",
    "GroundTruthRecord",
    "Mention",
    "artifacts_from_dicts",
    "claim_from_dict",
    "claim_to_dict",
    "load_artifacts_jsonl",
    "mention_from_dict",
    "mention_to_dict",
    "normalize_mention_text",
    "read_jsonl",
    "write_jsonl",
]
