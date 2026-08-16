"""Entity resolution package — Phase 3 founder-owned core.

    mention
      → EntityCandidate (surface form + identity signals)
      → CandidateIndex (cheap deterministic lookup, top-N)
      → FeatureVector (pluggable features; None = no evidence)
      → score_match (deterministic scoring table)
      → EntityResolver.resolve_pair (MERGE / KEEP_SEPARATE / REVIEW / ABSTAIN)
      → cluster → CanonicalEntity (aliases preserved, non-destructive)
      → bridge → resolutions format for claim loading (Phase 3 integration)

The resolver is deterministic and explainable. It does not consume the
teammate's candidate-pair feature files yet — the FeatureVector slots are
the plug-in points for those (embedding_similarity, cooccurrence, ...).
"""

from .candidates import CandidateIndex, candidate_from_mention
from .models import (
    CanonicalEntity,
    EntityCandidate,
    EntityMatch,
    FeatureVector,
    IdentitySignals,
    ResolutionDecision,
    ResolutionVerdict,
)
from .resolver import EntityResolver, MERGE_THRESHOLD, REVIEW_THRESHOLD, SEPARATE_THRESHOLD
from .scoring import compute_features, score_match

__all__ = [
    "CandidateIndex",
    "CanonicalEntity",
    "EntityCandidate",
    "EntityMatch",
    "EntityResolver",
    "FeatureVector",
    "IdentitySignals",
    "MERGE_THRESHOLD",
    "REVIEW_THRESHOLD",
    "SEPARATE_THRESHOLD",
    "ResolutionDecision",
    "ResolutionVerdict",
    "candidate_from_mention",
    "compute_features",
    "score_match",
]

from .store import EntityStore
from .pairs import IdentityPair, load_identity_pairs
from .bridge_claims import bridge_claim, bridge_claims
