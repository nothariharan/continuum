"""Deterministic candidate generation — cheap, before any expensive scoring.

Design principle: candidate generation must be cheap. Expensive reasoning
happens only on the ambiguous tail.

Pipeline for one mention:
    exact username
    → email local-part / full email
    → source external ID
    → normalized name (tokens)
    → lexicon aliases

Each known entity is indexed by every identity signal it carries; a query
mention hits the index by its own signals. Returns the top-N candidates
ranked by how many independent signals matched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .models import CanonicalEntity, EntityCandidate, IdentitySignals

_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def normalize_slug(text: str) -> str:
    """Collapse hyphens/spaces for project/account slug matching."""
    return _SLUG_RE.sub("", text.lower())


def normalize_tokens(text: str) -> set[str]:
    return set(_TOKEN_SPLIT_RE.split(text.lower())) - {""}


def local_part(email: str) -> str:
    return email.split("@")[0].replace("_", ".").replace("-", ".").replace(" ", ".")


def canonical_local(email: str) -> str:
    """Dot-normalized local part: ben_carter@x == ben.carter@y."""
    return _TOKEN_SPLIT_RE.sub(".", email.split("@")[0])


@dataclass
class CandidateIndex:
    """Inverted index over known entities by their identity signals."""

    by_email: dict[str, list[str]] = None
    by_local_email: dict[str, list[str]] = None
    by_username: dict[str, list[str]] = None
    by_username_base: dict[str, list[str]] = None
    by_external_id: dict[str, list[str]] = None
    by_name_token: dict[str, list[str]] = None
    _entities: dict[str, CanonicalEntity] = None

    def __post_init__(self) -> None:
        self.by_email = {}
        self.by_local_email = {}
        self.by_username = {}
        self.by_username_base = {}
        self.by_external_id = {}
        self.by_name_token = {}
        self._entities = {}

    @classmethod
    def build(cls, entities: Iterable[CanonicalEntity]) -> "CandidateIndex":
        index = cls()
        for entity in entities:
            index.add_entity(entity)
        return index

    def add_entity(self, entity: CanonicalEntity) -> None:
        self._entities[entity.entity_key] = entity
        for email in entity.emails:
            if "@" not in email or email.startswith("@") or email.endswith("@"):
                continue
            self.by_email.setdefault(email.lower(), []).append(entity.entity_key)
            self.by_local_email.setdefault(canonical_local(email), []).append(entity.entity_key)
        for username in entity.usernames:
            self.by_username.setdefault(username.lower(), []).append(entity.entity_key)
            from .scoring import username_base

            base = username_base(username)
            if base:
                self.by_username_base.setdefault(base, []).append(entity.entity_key)
        for external_id in entity.external_ids:
            self.by_external_id.setdefault(external_id.lower(), []).append(entity.entity_key)
        for alias in entity.aliases:
            for token in normalize_tokens(alias):
                self.by_name_token.setdefault(token, []).append(entity.entity_key)

    def lookup(self, signals: IdentitySignals, limit: int = 10) -> list[tuple[str, int]]:
        """Return (entity_key, matched_signal_count) for the top candidates."""
        from .scoring import username_base

        hits: dict[str, set[str]] = {}

        def bump(key: str, signal: str) -> None:
            if key in self._entities:
                hits.setdefault(key, set()).add(signal)

        for email in signals.emails:
            if "@" in email and not email.startswith("@") and not email.endswith("@"):
                for key in self.by_email.get(email.lower(), ()):
                    hits.setdefault(key, set()).add("email")
                for key in self.by_local_email.get(canonical_local(email), ()):
                    hits.setdefault(key, set()).add("email-local-part")
        for username in signals.usernames:
            for key in self.by_username.get(username.lower(), ()):
                hits.setdefault(key, set()).add("username")
            base = username_base(username)
            if base:
                for key in self.by_username_base.get(base, ()):
                    hits.setdefault(key, set()).add("username-base")
        for external_id in signals.external_ids:
            for key in self.by_external_id.get(external_id.lower(), ()):
                hits.setdefault(key, set()).add("external-id")
        for token in normalize_tokens(signals.mention):
            for key in self.by_name_token.get(token, ()):
                hits.setdefault(key, set()).add("name-token")

        ranked = sorted(
            ((key, len(signal_set)) for key, signal_set in hits.items()),
            key=lambda item: (-item[1], item[0]),
        )
        return ranked[:limit]


def signals_from_mention(mention: str, *, inventory_entry: dict | None = None) -> IdentitySignals:
    """Build identity signals from a surface mention (+ optional inventory row)."""
    entry = inventory_entry or {}
    emails: list[str] = list(entry.get("emails") or ())
    usernames: list[str] = list(entry.get("usernames") or ())
    external_ids: list[str] = list(entry.get("external_ids") or ())
    if "@" in mention and not mention.startswith("@"):
        if mention not in emails:
            emails.append(mention)
    elif mention.startswith("@"):
        if mention not in usernames:
            usernames.append(mention)
    return IdentitySignals(
        mention=mention,
        type=str(entry.get("type") or "person"),
        emails=tuple(emails),
        usernames=tuple(usernames),
        external_ids=tuple(external_ids),
        source=entry.get("source"),
    )


def candidate_from_mention(
    mention: str,
    *,
    type: str = "person",
    emails: Iterable[str] = (),
    usernames: Iterable[str] = (),
    external_ids: Iterable[str] = (),
    source: str | None = None,
    frequency: int = 0,
    context: str = "",
    candidate_id: str | None = None,
) -> EntityCandidate:
    signals = IdentitySignals(
        mention=mention,
        type=type,
        emails=tuple(emails),
        usernames=tuple(usernames),
        external_ids=tuple(external_ids),
        source=source,
        frequency=frequency,
        context=context,
    )
    import hashlib

    return EntityCandidate(
        candidate_id=candidate_id or f"cand:{hashlib.sha256(mention.encode()).hexdigest()[:16]}",
        signals=signals,
    )
