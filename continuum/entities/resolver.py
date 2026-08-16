"""Entity resolver — deterministic decision layer over scored candidate pairs.

Decision rules (conservative; false merges are the critical failure mode):

    MERGE           score >= MERGE_THRESHOLD (0.90)  — strong single-signal
                    (email local-part, external id) or full-name + any signal
    KEEP_SEPARATE   score <= SEPARATE_THRESHOLD (0.20) and both sides carry
                    >=2 distinct full-name tokens (distinct people)
    REVIEW          score between 0.50 and MERGE_THRESHOLD — real shared
                    evidence but not conclusive
    ABSTAIN         no evidence either way (score < 0.50 and not enough
                    full-name signal to call them distinct)

The resolver is deterministic and explainable: every verdict carries the
score, the signals that fired, and a reason string.

Usage:
    resolver = EntityResolver(canonical_entities)   # known entity lexicon
    verdict = resolver.resolve_pair(a, b)
    merged, reviewed, separate = resolver.cluster(mentions)
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from .candidates import CandidateIndex, normalize_tokens
from .models import (
    CanonicalEntity,
    EntityCandidate,
    ResolutionDecision,
    ResolutionVerdict,
)
from .scoring import compute_features, score_match

MERGE_THRESHOLD = 0.90
SEPARATE_THRESHOLD = 0.20
REVIEW_THRESHOLD = 0.50

ROLE_SUFFIX_RE = re.compile(
    r"\s*\((?:redwood\s+)?(?:ae|se|csm|pm|sre|devops|security|product|eng(?:ineering)?|ops|cto|legal)\)\s*$",
    re.IGNORECASE,
)


def _full_name_tokens(mention: str) -> set[str]:
    from .scoring import _mention_tokens

    return _mention_tokens(mention)


def _surname(mention: str) -> str | None:
    """Last word of a cleaned name: 'Sarah Chen' -> 'chen'."""
    cleaned = ROLE_SUFFIX_RE.sub("", mention.strip())
    if "@" in cleaned:
        cleaned = cleaned.split("@")[0]
    words = [w for w in re.split(r"[^a-z0-9]+", cleaned.lower()) if w]
    return words[-1] if len(words) >= 2 else None


def _first_name(mention: str) -> str | None:
    """First word of a cleaned name: 'Sarah Chen' -> 'sarah'."""
    cleaned = ROLE_SUFFIX_RE.sub("", mention.strip())
    words = [w for w in re.split(r"[^a-z0-9]+", cleaned.lower()) if w]
    return words[0] if words else None


def _first_names_match(a_first: str | None, b_first: str | None) -> bool:
    """First-name match with initial tolerance: 's' ~ 'soham'."""
    if not a_first or not b_first:
        return False
    if a_first == b_first:
        return True
    return a_first.startswith(b_first) or b_first.startswith(a_first)


class EntityResolver:
    def __init__(self, entities: Iterable[CanonicalEntity] = (), merge_threshold: float = MERGE_THRESHOLD) -> None:
        self._entities = {e.entity_key: e for e in entities}
        self._index = CandidateIndex.build(self._entities.values())
        self.merge_threshold = merge_threshold

    # ---- candidate lookup -------------------------------------------------

    def candidates_for(self, candidate: EntityCandidate, limit: int = 10) -> list[EntityCandidate]:
        """Top-N known entities matching a mention's signals (cheap)."""
        ranked = self._index.lookup(candidate.signals, limit=limit)
        return [self._entities[key] for key, _ in ranked if key != candidate.candidate_id]

    # ---- pair resolution ---------------------------------------------------

    def resolve_pair(
        self,
        a: EntityCandidate | CanonicalEntity,
        b: EntityCandidate | CanonicalEntity,
        extra_features: dict[str, float] | None = None,
    ) -> ResolutionVerdict:
        """Resolve one candidate pair to MERGE / KEEP_SEPARATE / REVIEW / ABSTAIN."""
        a_cand, b_cand = self._as_candidates(a, b)
        features = compute_features(a_cand, b_cand, extra=extra_features)
        match = score_match(a_cand, b_cand, features)
        score = match.score
        signals = match.signals

        if score >= self.merge_threshold:
            return ResolutionVerdict(
                a_id=a_cand.candidate_id,
                b_id=b_cand.candidate_id,
                decision=ResolutionDecision.MERGE,
                score=score,
                signals=signals,
                reason=f"strong identity evidence: {', '.join(signals) or 'score'}",
                confidence=score,
            )

        a_tokens = _full_name_tokens(a_cand.mention)
        b_tokens = _full_name_tokens(b_cand.mention)
        both_full_names = len(a_tokens) >= 2 and len(b_tokens) >= 2

        # Both full names with no identity signal:
        #   - same first name + different surnames -> distinct people
        #     (Maya Chen vs Maya Patel): shared first name is not identity
        #   - different first names -> distinct people even with a shared
        #     surname (Maya Chen vs Sarah Chen): shared surname is not identity
        if both_full_names:
            a_surname = _surname(a_cand.mention)
            b_surname = _surname(b_cand.mention)
            a_first = _first_name(a_cand.mention)
            b_first = _first_name(b_cand.mention)
            no_identity_signal = not (
                features.email_match == 1.0
                or features.email_username_match == 1.0
                or features.username_match == 1.0
                or features.external_id_match == 1.0
            )
            different_people = (
                (a_surname and b_surname and a_surname != b_surname)
                or not _first_names_match(a_first, b_first)
            )
            if no_identity_signal and different_people:
                return ResolutionVerdict(
                    a_id=a_cand.candidate_id,
                    b_id=b_cand.candidate_id,
                    decision=ResolutionDecision.KEEP_SEPARATE,
                    score=score,
                    signals=signals,
                    reason=f"full names with no identity signal ({a_first} {a_surname} vs {b_first} {b_surname})",
                    confidence=1.0 - score,
                )

        if score <= SEPARATE_THRESHOLD and both_full_names and not (a_tokens & b_tokens):
            return ResolutionVerdict(
                a_id=a_cand.candidate_id,
                b_id=b_cand.candidate_id,
                decision=ResolutionDecision.KEEP_SEPARATE,
                score=score,
                signals=signals,
                reason="distinct full names, no shared identity evidence",
                confidence=1.0 - score,
            )

        if score >= REVIEW_THRESHOLD:
            return ResolutionVerdict(
                a_id=a_cand.candidate_id,
                b_id=b_cand.candidate_id,
                decision=ResolutionDecision.REVIEW,
                score=score,
                signals=signals,
                reason=f"shared evidence but not conclusive ({', '.join(signals) or 'name overlap'})",
                confidence=score,
            )

        return ResolutionVerdict(
            a_id=a_cand.candidate_id,
            b_id=b_cand.candidate_id,
            decision=ResolutionDecision.ABSTAIN,
            score=score,
            signals=signals,
            reason="no conclusive evidence either way",
            confidence=0.0,
        )

    # ---- clustering ---------------------------------------------------------

    def cluster(
        self,
        candidates: Iterable[EntityCandidate],
        extra_features: dict[str, float] | None = None,
    ) -> dict[str, list[ResolutionVerdict]]:
        """Greedy clustering of mentions into canonical entities.

        Only MERGE verdicts cluster; REVIEW and ABSTAIN pairs are reported
        separately and never merged. Returns {"merged": CanonicalEntity list
        by key, "review": verdicts, "abstained": verdicts, "separate": verdicts}.
        """
        mentions = list(candidates)
        parent: dict[str, str] = {c.candidate_id: c.candidate_id for c in mentions}
        review: list[ResolutionVerdict] = []
        abstained: list[ResolutionVerdict] = []
        separate: list[ResolutionVerdict] = []

        def root(key: str) -> str:
            while parent[key] != key:
                parent[key] = parent[parent[key]]
                key = parent[key]
            return key

        for i in range(len(mentions)):
            for j in range(i + 1, len(mentions)):
                a, b = mentions[i], mentions[j]
                verdict = self.resolve_pair(a, b, extra_features=extra_features)
                if verdict.decision == ResolutionDecision.MERGE:
                    parent[root(a.candidate_id)] = root(b.candidate_id)
                elif verdict.decision == ResolutionDecision.REVIEW:
                    review.append(verdict)
                elif verdict.decision == ResolutionDecision.KEEP_SEPARATE:
                    separate.append(verdict)
                else:
                    abstained.append(verdict)

        # Anchored join: a REVIEW pair whose mention shares the cluster's
        # strong anchor (email/username/external id) may join it — but only
        # at the name-tokens tier (score >= 0.80, i.e. >= 2 shared tokens or
        # an identity-signal pair). Single-token (0.55) joins are exactly the
        # false-merge cascade source ("Maya" pulls in every Maya*), so they
        # stay REVIEW. Pairs flagged KEEP_SEPARATE never join.
        groups: dict[str, list[EntityCandidate]] = defaultdict(list)
        for candidate in mentions:
            groups[root(candidate.candidate_id)].append(candidate)

        def _has_anchor(candidate: EntityCandidate) -> bool:
            s = candidate.signals
            return bool(s.emails or s.usernames or s.external_ids)

        def _cluster_anchored(members: list[EntityCandidate]) -> bool:
            return any(_has_anchor(m) for m in members)

        changed = True
        while changed:
            changed = False
            for verdict in list(review):
                if verdict.score < 0.80:
                    continue
                a_ment = next((c for c in mentions if c.candidate_id == verdict.a_id), None)
                b_ment = next((c for c in mentions if c.candidate_id == verdict.b_id), None)
                if a_ment is None or b_ment is None:
                    continue
                ra, rb = root(a_ment.candidate_id), root(b_ment.candidate_id)
                if ra == rb:
                    review.remove(verdict)
                    changed = True
                    continue
                members_a = groups.get(ra, [])
                members_b = groups.get(rb, [])
                if _cluster_anchored(members_a) or _cluster_anchored(members_b):
                    parent[ra] = rb
                    groups[rb].extend(members_a)
                    groups.pop(ra, None)
                    review.remove(verdict)
                    changed = True

        merged: dict[str, CanonicalEntity] = {}
        for group in groups.values():
            if len(group) < 2:
                continue
            representative = group[0]
            entity = CanonicalEntity(
                entity_key=_canonical_key(representative),
                label=representative.type,
                name=representative.mention,
            )
            for candidate in group:
                entity.absorb(candidate)
            merged[entity.entity_key] = entity

        return {
            "merged": merged,
            "review": review,
            "abstained": abstained,
            "separate": separate,
        }

    # ---- helpers -------------------------------------------------------------

    def _as_candidates(self, a, b) -> tuple[EntityCandidate, EntityCandidate]:
        def to_candidate(item) -> EntityCandidate:
            if isinstance(item, CanonicalEntity):
                return EntityCandidate(
                    candidate_id=item.entity_key,
                    signals=__import__("continuum.entities.models", fromlist=["IdentitySignals"]).IdentitySignals(
                        mention=item.name,
                        type=item.label,
                        emails=tuple(item.emails),
                        usernames=tuple(item.usernames),
                        external_ids=tuple(item.external_ids),
                        source=next(iter(item.sources)) if item.sources else None,
                    ),
                )
            return item

        return to_candidate(a), to_candidate(b)


def _canonical_key(candidate: EntityCandidate) -> str:
    """Best-effort stable key for a cluster: person:first-last lowercased."""
    tokens = normalize_tokens(candidate.mention)
    label = candidate.type or "entity"
    stem = "-".join(sorted(tokens)) or "unknown"
    return f"{label}:{stem}"
