"""Cross-source evidence ranking and grouping (Section 10).

When several sources support the same fact we do NOT simply concatenate them.
Evidence is grouped around the resolved subject and ranked so the strongest,
most relevant item leads — the answer can then cite the top item and optionally
show the rest.

Ranking is honest: it uses only signals that actually exist — whether the item
supports the current resolved subject, its business observation time, and the
artifact kind (a formal record like an email confirmation outranks a chat
mention at the same recency). No confidence score is invented.
"""

from __future__ import annotations

from typing import Any

# Artifact kinds that represent a more formal / authoritative record. Used only
# as a tie-breaker at equal recency — never to override temporal evidence.
_KIND_WEIGHT = {
    "gmail_message": 2,
    "email": 2,
    "linear_ticket": 2,
    "jira_ticket": 2,
    "slack_message": 1,
}


def _kind_weight(item: dict[str, Any]) -> int:
    return _KIND_WEIGHT.get(str(item.get("artifact_kind") or "").lower(), 0)


def rank_evidence(
    evidence: list[dict[str, Any]],
    *,
    current_subject: str | None = None,
) -> list[dict[str, Any]]:
    """Return evidence ordered strongest-first.

    Order: items supporting the current resolved subject first, then most
    recent observation, then more formal artifact kind. Stable and
    deterministic; the input list is not mutated.
    """
    subject = (current_subject or "").strip().lower()

    def supports_current(item: dict[str, Any]) -> int:
        if not subject:
            return 0
        hay = f"{item.get('subject_mention') or ''} {item.get('subject_id') or ''}".lower()
        return 1 if subject in hay else 0

    return sorted(
        evidence,
        key=lambda e: (
            supports_current(e),
            str(e.get("observed_at") or ""),
            _kind_weight(e),
        ),
        reverse=True,
    )


def group_evidence_by_subject(evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group evidence items by the claimed subject (the value they support)."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        key = str(item.get("subject_mention") or item.get("subject_id") or "unknown")
        groups.setdefault(key, []).append(item)
    return groups


def evidence_sources(evidence: list[dict[str, Any]]) -> list[str]:
    """Distinct source systems present in the evidence, order-stable."""
    seen: list[str] = []
    for item in evidence:
        src = item.get("source")
        if src and src not in seen:
            seen.append(src)
    return seen


def summarize_cross_source(
    evidence: list[dict[str, Any]],
    *,
    current_subject: str | None = None,
) -> dict[str, Any]:
    """Rank + group evidence and report which sources corroborate the fact.

    ``multi_source`` is True when more than one source system supports the
    fact — the signal that a claim's memory spans Slack + Gmail rather than
    living in one connector.
    """
    ranked = rank_evidence(evidence, current_subject=current_subject)
    sources = evidence_sources(ranked)
    return {
        "ranked": ranked,
        "top": ranked[0] if ranked else None,
        "by_subject": group_evidence_by_subject(ranked),
        "sources": sources,
        "multi_source": len(sources) > 1,
    }
