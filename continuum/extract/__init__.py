"""Phase 2B mention and claim extraction."""

from .claim import ClaimExtractor, extract_claims
from .deterministic import DeterministicMentionExtractor
from .inventory import build_mention_inventory
from .mention import MentionExtractor, extract_mentions
from .schemas import Claim, GroundTruthRecord, Mention, claim_to_dict, mention_to_dict

__all__ = [
    "Claim",
    "ClaimExtractor",
    "DeterministicMentionExtractor",
    "GroundTruthRecord",
    "Mention",
    "MentionExtractor",
    "build_mention_inventory",
    "claim_to_dict",
    "extract_claims",
    "extract_mentions",
    "mention_to_dict",
]
