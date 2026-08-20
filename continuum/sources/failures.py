"""Cross-source ingestion failure taxonomy (Section 19).

Extends the extraction (``continuum.eval.failures``) and query
(``continuum.query.failures``) taxonomies with the ingestion / cross-source
view. The guiding rule: ingestion failures must be SURFACED, never hidden
behind empty results. Every failure maps to exactly one category so operators
can attribute a problem to a stage instead of seeing a silent zero.
"""

from __future__ import annotations

from typing import Any

# Ordered for stable reporting.
CROSS_SOURCE_FAILURES: tuple[str, ...] = (
    "GMAIL_INGESTION_FAILURE",       # generic Gmail API failure during fetch
    "GMAIL_AUTH_FAILURE",            # credentials/consent/token problem (401/403)
    "GMAIL_PARSE_FAILURE",           # a fetched message could not be normalized
    "CROSS_SOURCE_ER_FAILURE",       # identity resolution could not link/keep-apart safely
    "CROSS_SOURCE_TEMPORAL_FAILURE", # timestamps could not order events across sources
    "CROSS_SOURCE_CONFLICT",         # contradictory claims with no safe resolution
    "PROVENANCE_MISS",               # a claim/state lost its source chain
    "DUPLICATE_EVENT",               # the same source event arrived more than once
    "SAFE_ABSTENTION",               # deliberately declined to answer (NOT a failure)
)

DESCRIPTIONS: dict[str, str] = {
    "GMAIL_INGESTION_FAILURE": "Gmail API fetch failed (network / 5xx / unexpected).",
    "GMAIL_AUTH_FAILURE": "Gmail credentials, token, or consent invalid (401/403).",
    "GMAIL_PARSE_FAILURE": "A fetched Gmail message could not be normalized to an artifact.",
    "CROSS_SOURCE_ER_FAILURE": "Identity resolution could not safely link or separate entities across sources.",
    "CROSS_SOURCE_TEMPORAL_FAILURE": "Cross-source timestamps could not establish event ordering.",
    "CROSS_SOURCE_CONFLICT": "Contradictory claims across sources with no safe resolution.",
    "PROVENANCE_MISS": "A claim or state could not be traced back to a source artifact.",
    "DUPLICATE_EVENT": "The same source event was received more than once.",
    "SAFE_ABSTENTION": "The system deliberately abstained rather than guess (expected, not a failure).",
}

# Categories that are correct behavior, not defects.
NON_DEFECTS: frozenset[str] = frozenset({"SAFE_ABSTENTION"})


def is_defect(category: str) -> bool:
    """True when the category represents an actual failure to fix/alert on."""
    return category in CROSS_SOURCE_FAILURES and category not in NON_DEFECTS


def classify_gmail_error(exc: Exception) -> str:
    """Map a Gmail live/auth exception to a taxonomy category.

    Reads the ``code`` attribute set by ``GmailLiveError`` / ``GmailAuthError``
    where present; falls back to structural checks so callers never have to
    import the concrete error types.
    """
    code = getattr(exc, "code", None)
    if code in CROSS_SOURCE_FAILURES:
        return code
    name = type(exc).__name__
    if name == "GmailAuthError" or isinstance(exc, FileNotFoundError):
        return "GMAIL_AUTH_FAILURE"
    if name == "GmailLiveError":
        return "GMAIL_INGESTION_FAILURE"
    return "GMAIL_INGESTION_FAILURE"


def classify_state_status(status: str | None) -> str | None:
    """Map a resolved-state status to a cross-source taxonomy category.

    Returns None for statuses that are not cross-source failures (e.g.
    ``definitive``). ``conflict``/``review`` -> CROSS_SOURCE_CONFLICT,
    ``absent`` -> SAFE_ABSTENTION (declining is expected behavior).
    """
    if status in ("conflict", "review"):
        return "CROSS_SOURCE_CONFLICT"
    if status == "absent":
        return "SAFE_ABSTENTION"
    return None


def empty_taxonomy() -> dict[str, int]:
    """A zeroed counter over every category — makes 'zero' explicit, not silent."""
    return {category: 0 for category in CROSS_SOURCE_FAILURES}


def merge_taxonomy(base: dict[str, int], category: str, count: int = 1) -> dict[str, int]:
    """Increment ``category`` in ``base`` (validated against the taxonomy)."""
    if category not in CROSS_SOURCE_FAILURES:
        raise ValueError(f"unknown cross-source failure category: {category!r}")
    base[category] = base.get(category, 0) + count
    return base


__all__ = [
    "CROSS_SOURCE_FAILURES",
    "DESCRIPTIONS",
    "NON_DEFECTS",
    "classify_gmail_error",
    "classify_state_status",
    "empty_taxonomy",
    "is_defect",
    "merge_taxonomy",
]
