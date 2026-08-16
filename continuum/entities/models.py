"""Entity resolution core models — Phase 3 (founder-owned).

The canonical objects of the entity-resolution subsystem:

- IdentitySignals   structured identity evidence attached to a mention
- EntityCandidate   a mention surface form + its identity signals
- EntityMatch       a scored candidate pair
- CanonicalEntity   the resolved, merged entity (aliases preserved)
- ResolutionDecision  MERGE / KEEP_SEPARATE / REVIEW / ABSTAIN
- ResolutionVerdict the outcome of resolving one pair or one mention

Design rules:
- The source representation is never destroyed: CanonicalEntity keeps every
  alias, mention, and signal that led to the merge.
- Nothing here touches HydraDB or the claim contract; this package is pure
  Python over in-memory structures. Graph integration is a separate layer
  (continuum/entities/bridge.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class IdentitySignals:
    """Identity evidence attached to a mention surface form."""

    mention: str
    type: str = "person"                # person / email / username / account / ...
    emails: tuple[str, ...] = ()
    usernames: tuple[str, ...] = ()
    external_ids: tuple[str, ...] = ()  # source-specific ids (github handle, hubspot id, ...)
    source: str | None = None           # which source system the mention came from
    frequency: int = 0                  # how often the mention appeared
    context: str = ""                   # optional surrounding text

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IdentitySignals":
        return cls(
            mention=str(data.get("mention", "")),
            type=str(data.get("type", "person")),
            emails=tuple(data.get("emails") or ()),
            usernames=tuple(data.get("usernames") or ()),
            external_ids=tuple(data.get("external_ids") or ()),
            source=data.get("source"),
            frequency=int(data.get("frequency") or 0),
            context=str(data.get("context") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mention": self.mention,
            "type": self.type,
            "emails": list(self.emails),
            "usernames": list(self.usernames),
            "external_ids": list(self.external_ids),
            "source": self.source,
            "frequency": self.frequency,
            "context": self.context,
        }


@dataclass(frozen=True)
class EntityCandidate:
    """A mention surface form plus its identity signals (pre-resolution)."""

    candidate_id: str
    signals: IdentitySignals

    @property
    def mention(self) -> str:
        return self.signals.mention

    @property
    def type(self) -> str:
        return self.signals.type

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "signals": self.signals.to_dict()}


@dataclass(frozen=True)
class FeatureVector:
    """Pluggable feature vector for a candidate pair.

    Every feature is in [0, 1] or None when the feature could not be computed
    (e.g. embedding similarity before embeddings exist). None never implies
    0 — it implies "no evidence either way" and must be treated as neutral.
    """

    name_similarity: float | None = None
    email_match: float | None = None
    email_username_match: float | None = None
    username_match: float | None = None
    external_id_match: float | None = None
    source_overlap: float | None = None
    cooccurrence: float | None = None
    embedding_similarity: float | None = None
    extra: dict[str, float] = field(default_factory=dict)

    def available(self, name: str) -> bool:
        value = getattr(self, name, None)
        return value is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name_similarity": self.name_similarity,
            "email_match": self.email_match,
            "email_username_match": self.email_username_match,
            "username_match": self.username_match,
            "external_id_match": self.external_id_match,
            "source_overlap": self.source_overlap,
            "cooccurrence": self.cooccurrence,
            "embedding_similarity": self.embedding_similarity,
            **self.extra,
        }


@dataclass(frozen=True)
class EntityMatch:
    """A scored candidate pair."""

    a: EntityCandidate
    b: EntityCandidate
    features: FeatureVector
    score: float = 0.0
    signals: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "a": self.a.to_dict(),
            "b": self.b.to_dict(),
            "features": self.features.to_dict(),
            "score": round(self.score, 4),
            "signals": list(self.signals),
        }


class ResolutionDecision(Enum):
    MERGE = "MERGE"
    KEEP_SEPARATE = "KEEP_SEPARATE"
    REVIEW = "REVIEW"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class ResolutionVerdict:
    """Outcome of resolving one candidate pair (or one mention)."""

    a_id: str
    b_id: str
    decision: ResolutionDecision
    score: float = 0.0
    signals: tuple[str, ...] = ()
    reason: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "a": self.a_id,
            "b": self.b_id,
            "decision": self.decision.value,
            "score": round(self.score, 4),
            "signals": list(self.signals),
            "reason": self.reason,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class CanonicalEntity:
    """The resolved entity. Non-destructive: keeps every alias and signal."""

    entity_key: str          # e.g. person:soham-ratnaparkhi
    label: str               # Person / Account / Project / ...
    name: str                # display name (best-known form)
    aliases: set[str] = field(default_factory=set)
    mentions: set[str] = field(default_factory=set)
    emails: set[str] = field(default_factory=set)
    usernames: set[str] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    members: list[str] = field(default_factory=list)  # candidate_ids merged in

    def absorb(self, candidate: EntityCandidate) -> None:
        """Merge a candidate's signals into this entity (never deletes)."""
        signals = candidate.signals
        self.mentions.add(signals.mention)
        self.aliases.add(signals.mention)
        self.emails.update(signals.emails)
        self.usernames.update(signals.usernames)
        self.external_ids.update(signals.external_ids)
        if signals.source:
            self.sources.add(signals.source)
        self.members.append(candidate.candidate_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_key": self.entity_key,
            "label": self.label,
            "name": self.name,
            "aliases": sorted(self.aliases),
            "mentions": sorted(self.mentions),
            "emails": sorted(self.emails),
            "usernames": sorted(self.usernames),
            "external_ids": sorted(self.external_ids),
            "sources": sorted(self.sources),
            "members": sorted(self.members),
        }
