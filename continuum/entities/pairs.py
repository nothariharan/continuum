"""Identity-pair gold dataset contract — the teammate->resolver handoff.

The teammate produces `data/entity_resolution/identity-pairs.jsonl` with one
row per candidate pair:

    {
      "pair_id": "ip-001",
      "mention_a": "Sam",
      "type_a": "person",
      "source_a": "slack",
      "emails_a": [],
      "usernames_a": [],
      "external_ids_a": [],
      "mention_b": "@soham",
      "type_b": "person",
      "source_b": "slack",
      "emails_b": [],
      "usernames_b": ["soham"],
      "external_ids_b": [],
      "label": "SAME_ENTITY",          # SAME_ENTITY | DIFFERENT_ENTITY | UNCERTAIN
      "features": {
        "email_match": null,           # 0..1 or null (null = not measured)
        "username_match": 1.0,
        "external_id_match": null,
        "name_similarity": null,
        "first_name_match": null,
        "surname_match": null,
        "shared_project": null,
        "shared_repository": null,
        "shared_channel": null,
        "source_overlap": null,
        "cooccurrence_score": null,
        "embedding_similarity": null
      },
      "notes": "..."
    }

The resolver consumes this file via `load_identity_pairs`; every row becomes
a candidate pair whose features merge into the deterministic FeatureVector
(teammate-measured values override; missing slots fall back to the
deterministic computation). The resolver never invents features.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .candidates import candidate_from_mention
from .models import EntityCandidate, FeatureVector, IdentitySignals
from .scoring import compute_features

LABELS = frozenset({"SAME_ENTITY", "DIFFERENT_ENTITY", "UNCERTAIN"})

FEATURE_NAMES = (
    "email_match",
    "username_match",
    "external_id_match",
    "name_similarity",
    "first_name_match",
    "surname_match",
    "shared_project",
    "shared_repository",
    "shared_channel",
    "source_overlap",
    "cooccurrence_score",
    "embedding_similarity",
)


@dataclass(frozen=True)
class IdentityPair:
    pair_id: str
    mention_a: str
    type_a: str = "person"
    source_a: str | None = None
    emails_a: tuple[str, ...] = ()
    usernames_a: tuple[str, ...] = ()
    external_ids_a: tuple[str, ...] = ()
    mention_b: str = ""
    type_b: str = "person"
    source_b: str | None = None
    emails_b: tuple[str, ...] = ()
    usernames_b: tuple[str, ...] = ()
    external_ids_b: tuple[str, ...] = ()
    label: str = "UNCERTAIN"
    features: dict[str, float | None] = field(default_factory=dict)
    notes: str = ""

    def validate(self) -> None:
        if self.label not in LABELS:
            raise ValueError(f"{self.pair_id}: label {self.label!r} not in {sorted(LABELS)}")
        if not self.mention_a.strip() or not self.mention_b.strip():
            raise ValueError(f"{self.pair_id}: both mentions must be non-empty")
        for name in self.features:
            value = self.features[name]
            if value is not None and not (0.0 <= float(value) <= 1.0):
                raise ValueError(f"{self.pair_id}: feature {name}={value!r} outside [0,1]")

    @property
    def label_same(self) -> bool:
        return self.label == "SAME_ENTITY"

    @property
    def label_different(self) -> bool:
        return self.label == "DIFFERENT_ENTITY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "mention_a": self.mention_a,
            "type_a": self.type_a,
            "source_a": self.source_a,
            "emails_a": list(self.emails_a),
            "usernames_a": list(self.usernames_a),
            "external_ids_a": list(self.external_ids_a),
            "mention_b": self.mention_b,
            "type_b": self.type_b,
            "source_b": self.source_b,
            "emails_b": list(self.emails_b),
            "usernames_b": list(self.usernames_b),
            "external_ids_b": list(self.external_ids_b),
            "label": self.label,
            "features": self.features,
            "notes": self.notes,
        }

    def candidate_a(self) -> EntityCandidate:
        return candidate_from_mention(
            mention=self.mention_a,
            type=self.type_a,
            emails=self.emails_a,
            usernames=self.usernames_a,
            external_ids=self.external_ids_a,
            source=self.source_a,
            candidate_id=f"pair:{self.pair_id}:a",
        )

    def candidate_b(self) -> EntityCandidate:
        return candidate_from_mention(
            mention=self.mention_b,
            type=self.type_b,
            emails=self.emails_b,
            usernames=self.usernames_b,
            external_ids=self.external_ids_b,
            source=self.source_b,
            candidate_id=f"pair:{self.pair_id}:b",
        )

    def merged_features(self) -> FeatureVector:
        """FeatureVector for scoring: teammate-measured evidence merged over
        the deterministic computation.

        Contract rules:
        - Guarded slots (email/username/external_id/source) come from the
          deterministic computation when it has a signal — it carries the
          role-mailbox and invalid-email guards that prevent false merges.
        - When the deterministic layer has NO signal for a guarded slot
          (None), the teammate's measured value is honored: measurements can
          add evidence the deterministic rules cannot see (e.g. username on
          one side only, or "Sam is @soham's first-name form").
        - Evidence slots (cooccurrence, embedding_similarity, shared_*) come
          from the file — measurements the deterministic layer cannot produce.
        """
        a, b = self.candidate_a(), self.candidate_b()
        base = compute_features(a, b)
        from .scoring import is_role_mailbox_pair

        def merge(base_value, measured_value, *, guarded: bool = False):
            if base_value is not None:
                return base_value  # deterministic signal wins when present
            if guarded:
                return None       # a guard blocked this slot; measurement must not bypass it
            return measured_value  # measurement fills the evidence gap

        use_file_name = self.features.get("name_similarity") is not None
        email_guarded = is_role_mailbox_pair(a.signals, b.signals)
        return FeatureVector(
            name_similarity=self.features.get("name_similarity") if use_file_name else base.name_similarity,
            email_match=merge(base.email_match, self.features.get("email_match"), guarded=email_guarded),
            email_username_match=base.email_username_match,
            username_match=merge(base.username_match, self.features.get("username_match")),
            external_id_match=merge(base.external_id_match, self.features.get("external_id_match")),
            source_overlap=merge(base.source_overlap, self.features.get("source_overlap")),
            cooccurrence=self.features.get("cooccurrence_score"),
            embedding_similarity=self.features.get("embedding_similarity"),
            extra={
                "shared_project": self.features.get("shared_project"),
                "shared_repository": self.features.get("shared_repository"),
                "shared_channel": self.features.get("shared_channel"),
                "first_name_match": self.features.get("first_name_match"),
                "surname_match": self.features.get("surname_match"),
            },
        )


def load_identity_pairs(path: Path | str) -> list[IdentityPair]:
    pairs = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            pair = IdentityPair(
                pair_id=str(row.get("pair_id", f"line-{line_number}")),
                mention_a=str(row.get("mention_a", "")),
                type_a=str(row.get("type_a", "person")),
                source_a=row.get("source_a"),
                emails_a=tuple(row.get("emails_a") or ()),
                usernames_a=tuple(row.get("usernames_a") or ()),
                external_ids_a=tuple(row.get("external_ids_a") or ()),
                mention_b=str(row.get("mention_b", "")),
                type_b=str(row.get("type_b", "person")),
                source_b=row.get("source_b"),
                emails_b=tuple(row.get("emails_b") or ()),
                usernames_b=tuple(row.get("usernames_b") or ()),
                external_ids_b=tuple(row.get("external_ids_b") or ()),
                label=str(row.get("label", "UNCERTAIN")),
                features=dict(row.get("features") or {}),
                notes=str(row.get("notes", "")),
            )
            pair.validate()
            pairs.append(pair)
    return pairs


# Teammate row format: {"a": {mention, type, emails, usernames, external_ids,
# sources, frequency}, "b": {...}, "label", "features": {cooccurrence, ...}}
_NESTED_KEYS = {
    "mention": "mention",
    "type": "type",
    "emails": "emails",
    "usernames": "usernames",
    "external_ids": "external_ids",
    "sources": "sources",
}

_FEATURE_ALIASES = {
    "cooccurrence": "cooccurrence_score",
}


def _nested_side(row: dict, side: str) -> dict:
    return dict(row.get(side) or {})


def load_teammate_identity_pairs(path: Path | str) -> list[IdentityPair]:
    """Adapter for the teammate's identity-pairs.jsonl format.

    The teammate emits rows as {"a": {...}, "b": {...}, "label", "features"}
    with features keyed `cooccurrence`; the founder contract uses flat
    mention_a/mention_b and `cooccurrence_score`. This adapter maps the file
    onto the contract WITHOUT changing feature meaning, and validates every
    row through IdentityPair.validate (label, ranges, non-empty mentions).
    """
    pairs = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "a" not in row or "b" not in row:
                raise ValueError(f"line {line_number}: expected nested a/b row format")
            a, b = row["a"], row["b"]
            features = dict(row.get("features") or {})
            renamed = {
                _FEATURE_ALIASES.get(key, key): value
                for key, value in features.items()
            }
            pair = IdentityPair(
                pair_id=str(row.get("pair_id", f"line-{line_number}")),
                mention_a=str(a.get("mention", "")),
                type_a=str(a.get("type", "person")),
                source_a=_first_source(a),
                emails_a=tuple(a.get("emails") or ()),
                usernames_a=tuple(a.get("usernames") or ()),
                external_ids_a=tuple(a.get("external_ids") or ()),
                mention_b=str(b.get("mention", "")),
                type_b=str(b.get("type", "person")),
                source_b=_first_source(b),
                emails_b=tuple(b.get("emails") or ()),
                usernames_b=tuple(b.get("usernames") or ()),
                external_ids_b=tuple(b.get("external_ids") or ()),
                label=str(row.get("label", "UNCERTAIN")),
                features=renamed,
                notes=row.get("label_rationale", "") or str(row.get("difficulty_tags", "")),
            )
            pair.validate()
            pairs.append(pair)
    return pairs


def _first_source(side: dict) -> str | None:
    sources = side.get("sources") or []
    return str(sources[0]) if sources else None


def write_identity_pairs(path: Path | str, pairs: Iterable[IdentityPair]) -> int:
    count = 0
    with Path(path).open("w", encoding="utf-8") as handle:
        for pair in pairs:
            handle.write(json.dumps(pair.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count
