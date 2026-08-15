"""Shared Phase 2B contract: Artifact / Mention / Claim.

Canonical dataclasses live in `schema.py`; `continuum/extract/schemas.py`
re-exports them so the extraction pipeline and the graph pipeline share one
definition. Validation is in `validate.py`; JSONL interchange in `io.py`.

This package is team-owned. The founder defines and locks the contract; the
teammate's extraction pipeline consumes it. Changes require team agreement.
"""

from .io import load_claims, load_mentions, read_jsonl, write_jsonl
from .schema import (
    SUPPORTED_MENTION_TYPES,
    SUPPORTED_PREDICATES,
    Claim,
    Mention,
    stable_hash,
)
from .validate import ContractError, validate_claim, validate_mention

__all__ = [
    "Claim",
    "ContractError",
    "Mention",
    "SUPPORTED_MENTION_TYPES",
    "SUPPORTED_PREDICATES",
    "load_claims",
    "load_mentions",
    "read_jsonl",
    "stable_hash",
    "validate_claim",
    "validate_mention",
    "write_jsonl",
]
