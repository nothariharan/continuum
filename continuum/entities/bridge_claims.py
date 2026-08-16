"""Claim -> canonical entity bridge (Phase 3B).

The Claim remains the evidence; the canonical relationship is derived graph
state. This bridge maps a claim's subject/object mentions to canonical
entity keys via the EntityStore, producing the canonical view of a claim:

    {
      "claim_id": ...,
      "subject_mention": "Sarah",
      "subject_entity": "person:sarah-chen",     # resolved
      "object_mention": "Acme",
      "object_entity": "account:acme-health",    # resolved
      "predicate": "OWNS",
      ...
    }

Unresolved mentions are explicit: subject_entity / object_entity are None
and the claim is flagged for REVIEW — never silently dropped, never guessed.
"""

from __future__ import annotations

from typing import Any

from .store import EntityStore


def bridge_claim(store: EntityStore, claim: dict[str, Any]) -> dict[str, Any]:
    """Resolve a claim's mentions to canonical entities via the store.

    Never deletes the original mentions — it adds canonical identity on top.
    """
    subject_mention = claim.get("subject_mention", "")
    object_mention = claim.get("object_mention", "")

    subject = store.resolve_mention(subject_mention)
    object_ = store.resolve_mention(object_mention)

    out = dict(claim)
    out["subject_entity"] = subject.get("entity_key")
    out["object_entity"] = object_.get("entity_key")
    out["subject_resolved"] = subject.get("status") == "definitive"
    out["object_resolved"] = object_.get("status") == "definitive"
    out["resolution_status"] = (
        "resolved" if out["subject_resolved"] and out["object_resolved"]
        else "review" if out["subject_resolved"] or out["object_resolved"]
        else "unresolved"
    )
    return out


def bridge_claims(store: EntityStore, claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [bridge_claim(store, claim) for claim in claims]


def summary(bridged: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = sum(1 for c in bridged if c["resolution_status"] == "resolved")
    review = sum(1 for c in bridged if c["resolution_status"] == "review")
    unresolved = sum(1 for c in bridged if c["resolution_status"] == "unresolved")
    return {
        "claims": len(bridged),
        "resolved": resolved,
        "review": review,
        "unresolved": unresolved,
        "resolve_rate": round(resolved / len(bridged), 4) if bridged else 0.0,
    }
