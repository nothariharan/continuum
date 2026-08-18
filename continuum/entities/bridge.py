"""Bridge: resolved canonical entities -> the Phase 2B resolutions format.

The claim-loading boundary (`continuum/hydradb/claims.load_claims`) consumes
a resolutions map:

    {
      "person:soham-ratnaparkhi": {
        "name": "Soham Ratnaparkhi",
        "label": "Person",
        "mentions": ["Soham Ratnaparkhi", "@soham", ...],
        "aliases": [...],
      },
      ...
    }

This module converts a set of CanonicalEntity objects into exactly that
shape, so Phase 3 resolution output can flow into the existing, unchanged
claim ingestion path. Mentions are unioned from every surface form the
entity absorbed; nothing is deleted.
"""

from __future__ import annotations

from typing import Iterable

from .models import CanonicalEntity

LABEL_MAP = {
    "person": "Person",
    "account": "Account",
    "project": "Project",
    "service": "Service",
    "team": "Team",
    "org": "Account",
}


def canonical_label(entity: CanonicalEntity) -> str:
    return LABEL_MAP.get(entity.label.lower(), entity.label or "Person")


def to_resolutions(entities: Iterable[CanonicalEntity]) -> dict[str, dict]:
    """Convert canonical entities to the resolutions map consumed by load_claims.

    Note: a claim's subject_mention/object_mention must appear in a
    resolution's `mentions` list exactly, so every absorbed mention and alias
    is exposed as a resolvable mention.
    """
    resolutions: dict[str, dict] = {}
    for entity in entities:
        label = canonical_label(entity)
        # Identity surface forms are all resolvable mentions: verbatim
        # mentions/aliases plus emails and usernames (Slack handles and
        # Gmail local-parts are how a mention appears in source text).
        mentions = sorted(entity.mentions | entity.aliases | entity.emails | entity.usernames)
        if not mentions:
            continue
        resolutions[entity.entity_key] = {
            "name": entity.name,
            "label": label,
            "mentions": mentions,
            "aliases": sorted(entity.usernames | entity.external_ids),
        }
    return resolutions
