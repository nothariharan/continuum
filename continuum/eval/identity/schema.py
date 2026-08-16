"""Identity-pair gold dataset v1 — row schema and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterator

DATASET_VERSION = "v1"

IDENTITY_LABELS = frozenset({"SAME_ENTITY", "DIFFERENT_ENTITY", "UNCERTAIN"})

FEATURE_SLOTS = (
    "name_similarity",
    "email_match",
    "email_username_match",
    "username_match",
    "external_id_match",
    "source_overlap",
    "cooccurrence",
    "embedding_similarity",
    "shared_project",
    "shared_repository",
    "shared_channel",
)

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "entity_resolution" / "v1" / "identity-pairs.jsonl"
)
DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "entity_resolution"
    / "v1"
    / "identity-pairs-schema.json"
)


class IdentityLabel(str, Enum):
    SAME_ENTITY = "SAME_ENTITY"
    DIFFERENT_ENTITY = "DIFFERENT_ENTITY"
    UNCERTAIN = "UNCERTAIN"


LEGACY_LABEL_MAP = {
    "same": IdentityLabel.SAME_ENTITY.value,
    "different": IdentityLabel.DIFFERENT_ENTITY.value,
    "uncertain": IdentityLabel.UNCERTAIN.value,
}


@dataclass(frozen=True)
class MentionSide:
    mention: str
    type: str = "person"
    emails: tuple[str, ...] = ()
    usernames: tuple[str, ...] = ()
    external_ids: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    frequency: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mention": self.mention,
            "type": self.type,
            "emails": list(self.emails),
            "usernames": list(self.usernames),
            "external_ids": list(self.external_ids),
            "sources": list(self.sources),
            "frequency": self.frequency,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MentionSide":
        return cls(
            mention=str(data.get("mention", "")),
            type=str(data.get("type", "person")),
            emails=tuple(data.get("emails") or ()),
            usernames=tuple(data.get("usernames") or ()),
            external_ids=tuple(data.get("external_ids") or ()),
            sources=tuple(data.get("sources") or ()),
            frequency=int(data.get("frequency") or 0),
        )


@dataclass
class IdentityPairRow:
    pair_id: str
    a: MentionSide
    b: MentionSide
    label: str
    difficulty_tags: list[str] = field(default_factory=list)
    label_rationale: str = ""
    candidate_source: str = "legacy-labels"
    features: dict[str, float | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "pair_id": self.pair_id,
            "a": self.a.to_dict(),
            "b": self.b.to_dict(),
            "label": self.label,
            "difficulty_tags": list(self.difficulty_tags),
            "label_rationale": self.label_rationale,
            "candidate_source": self.candidate_source,
        }
        if self.features:
            row["features"] = self.features
        return row

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IdentityPairRow":
        return cls(
            pair_id=str(data["pair_id"]),
            a=MentionSide.from_dict(data["a"]),
            b=MentionSide.from_dict(data["b"]),
            label=str(data["label"]),
            difficulty_tags=list(data.get("difficulty_tags") or []),
            label_rationale=str(data.get("label_rationale") or data.get("note") or ""),
            candidate_source=str(data.get("candidate_source") or "legacy-labels"),
            features=dict(data.get("features") or {}),
        )


def normalize_difficulty_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip().lower().replace(" ", "_").replace("-", "_")
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def pair_key(a_mention: str, b_mention: str) -> tuple[str, str]:
    return tuple(sorted((a_mention, b_mention)))


def validate_identity_pair(row: dict[str, Any], *, require_features: bool = False) -> list[str]:
    errors: list[str] = []

    for field_name in ("pair_id", "a", "b", "label"):
        if field_name not in row:
            errors.append(f"missing field: {field_name}")

    if row.get("label") not in IDENTITY_LABELS:
        errors.append(f"invalid label: {row.get('label')}")

    for side_name in ("a", "b"):
        side = row.get(side_name)
        if not isinstance(side, dict):
            errors.append(f"{side_name} must be an object")
            continue
        if not side.get("mention"):
            errors.append(f"{side_name}.mention is required")

    features = row.get("features")
    if require_features:
        if not isinstance(features, dict):
            errors.append("features object is required")
        else:
            for slot in FEATURE_SLOTS:
                if slot not in features:
                    errors.append(f"features missing slot: {slot}")
                elif features[slot] is not None and not isinstance(features[slot], (int, float)):
                    errors.append(f"features.{slot} must be numeric or null")

    return errors


def validate_identity_pairs(
    rows: list[dict[str, Any]],
    *,
    require_features: bool = False,
    min_count: int = 75,
    max_count: int = 150,
) -> list[str]:
    errors: list[str] = []
    if len(rows) < min_count or len(rows) > max_count:
        errors.append(f"pair count {len(rows)} outside [{min_count}, {max_count}]")

    labels_seen: set[str] = set()
    pair_ids: set[str] = set()
    mention_pairs: set[tuple[str, str]] = set()

    for row in rows:
        errors.extend(validate_identity_pair(row, require_features=require_features))
        labels_seen.add(str(row.get("label")))
        pair_ids.add(str(row.get("pair_id")))
        a = row.get("a") or {}
        b = row.get("b") or {}
        key = pair_key(str(a.get("mention", "")), str(b.get("mention", "")))
        if key in mention_pairs:
            errors.append(f"duplicate mention pair: {key[0]} / {key[1]}")
        mention_pairs.add(key)

    if pair_ids and len(pair_ids) != len(rows):
        errors.append("duplicate pair_id values")

    missing_labels = IDENTITY_LABELS - labels_seen
    if missing_labels:
        errors.append(f"missing label values: {sorted(missing_labels)}")

    return errors


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterator[dict[str, Any] | IdentityPairRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = row.to_dict() if isinstance(row, IdentityPairRow) else row
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def load_identity_pairs(path: Path | None = None) -> list[dict[str, Any]]:
    return read_jsonl(path or DEFAULT_DATASET_PATH)


def write_identity_pairs(rows: list[IdentityPairRow | dict[str, Any]], path: Path | None = None) -> Path:
    target = path or DEFAULT_DATASET_PATH
    write_jsonl(target, rows)
    return target
