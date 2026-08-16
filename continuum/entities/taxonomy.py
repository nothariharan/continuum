"""Entity-resolution error taxonomy (Phase 3B).

When a pair resolves incorrectly, classify the failure mode so fixes target
real causes instead of random score tweaks:

    FALSE_MERGE_EMAIL            merged on coincidental email local part
    FALSE_MERGE_NAME             merged on shared name tokens
    FALSE_MERGE_ROLE_MAILBOX     merged two functional mailboxes
    FALSE_MERGE_SHARED_PROJECT   merged on project co-occurrence
    FALSE_MERGE_TOKEN_OVERLAP    merged on accidental token overlap
    FALSE_SPLIT_ALIAS            kept separate despite known alias
    FALSE_SPLIT_INITIALS         kept separate despite initial-name match
    FALSE_SPLIT_USERNAME         kept separate despite username link
    FALSE_SPLIT_CROSS_SOURCE_ID  kept separate despite shared external id
    REVIEW_AMBIGUOUS             correctly routed to review (not an error)
    ABSTAIN_INSUFFICIENT_EVIDENCE correctly abstained (not an error)

The classifier is heuristic: it inspects the pair's features and signals to
name the mechanism behind a wrong decision.
"""

from __future__ import annotations

from typing import Any

from .models import ResolutionDecision
from .pairs import IdentityPair


def classify_error(pair: IdentityPair, decision: ResolutionDecision, signals: tuple[str, ...]) -> str | None:
    """Return the error class for an incorrect decision, or None if correct.

    `signals` are the resolver's fired signals; the pair carries the measured
    features so the classifier can name the mechanism.
    """
    gold = pair.label
    features = pair.features or {}
    signal_set = set(signals)

    if gold == "SAME_ENTITY":
        if decision == ResolutionDecision.MERGE:
            return None  # correct
        # false split — name the mechanism
        if any(s in signal_set for s in ("username", "email-local-part", "email-username", "external-id")):
            if "username" in signal_set:
                return "FALSE_SPLIT_USERNAME"
            if "email-username" in signal_set or "email-local-part" in signal_set:
                return "FALSE_SPLIT_ALIAS"
            return "FALSE_SPLIT_CROSS_SOURCE_ID"
        if features.get("first_name_match") == 1.0 or features.get("surname_match") == 1.0:
            return "FALSE_SPLIT_INITIALS"
        if features.get("name_similarity", 0) or 0 >= 0.5:
            return "FALSE_SPLIT_INITIALS"
        return "FALSE_SPLIT_ALIAS"

    if gold == "DIFFERENT_ENTITY":
        if decision == ResolutionDecision.KEEP_SEPARATE:
            return None  # correct
        if decision == ResolutionDecision.MERGE:
            if any("mailbox" in str(k).lower() for k in (features or {})) or any(
                "procurement" in str(v).lower() for v in pair.emails_a + pair.emails_b
            ):
                return "FALSE_MERGE_ROLE_MAILBOX"
            if "email-local-part" in signal_set or features.get("email_match") == 1.0:
                return "FALSE_MERGE_EMAIL"
            if features.get("shared_project") == 1.0 or features.get("shared_repository") == 1.0:
                return "FALSE_MERGE_SHARED_PROJECT"
            if "name-token-single" in signal_set or (features.get("name_similarity") or 0) < 0.5:
                return "FALSE_MERGE_TOKEN_OVERLAP"
            return "FALSE_MERGE_NAME"
        # REVIEW / ABSTAIN on a DIFFERENT pair is a SAFE non-merge (no graph
        # corruption). Classify the mechanism, but it is not a false merge.
        if decision == ResolutionDecision.REVIEW:
            return "REVIEW_AMBIGUOUS"
        return "ABSTAIN_INSUFFICIENT_EVIDENCE"

    # UNCERTAIN gold
    if decision in {ResolutionDecision.REVIEW, ResolutionDecision.ABSTAIN}:
        return None  # correct routing
    if decision == ResolutionDecision.MERGE:
        return "FALSE_MERGE_NAME"
    return "FALSE_SPLIT_ALIAS"


def classify_rows(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group error-classified eval rows by taxonomy class."""
    from collections import defaultdict

    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get("error_class"):
            groups[row["error_class"]].append(row.get("pair_id", ""))
    return dict(groups)
