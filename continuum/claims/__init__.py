"""Shared Phase 2B contract: Artifact / Mention / Claim.

Artifact lives in `continuum.dataset.artifact`; Mention and Claim are defined
in `schema.py`, validated by `validate.py`, and exchanged via JSONL (`io.py`).

This package is team-owned. The founder defines and locks the contract; the
teammate's extraction pipeline consumes it. Changes require team agreement.
"""

from .io import load_claims, load_mentions, read_jsonl, write_jsonl
from .schema import Claim, Mention
from .validate import ContractError, validate_claim, validate_mention

__all__ = [
    "Claim",
    "ContractError",
    "Mention",
    "load_claims",
    "load_mentions",
    "read_jsonl",
    "validate_claim",
    "validate_mention",
    "write_jsonl",
]
