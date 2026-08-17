"""Query failure taxonomy — why a question was not answered well.

Complements the extraction/eval failure taxonomies with a query-side view.
Every pipeline result is classified into exactly one category so benchmark
and product diagnostics can attribute failures to a stage:

    RETRIEVAL_MISS            no candidate evidence scoped at all
    ENTITY_RESOLUTION_MISS    mention(s) could not be resolved
    TEMPORAL_MISS             requested time window has no state
    CONFLICT_MISS             claims conflict / ordering unknown
    PROVENANCE_MISS           answer asked for evidence, none available
    INSUFFICIENT_EVIDENCE     candidates exist but no claim supports state
    ANSWER_GENERATION_MISS    state resolved but no answer text produced
    SAFE_ABSTENTION           system explicitly abstained (not a failure)
    OK                        answered from resolved state/evidence
    INFRASTRUCTURE_ERROR      the pipeline raised
"""

from __future__ import annotations

from typing import Any

CATEGORIES = (
    "OK",
    "RETRIEVAL_MISS",
    "ENTITY_RESOLUTION_MISS",
    "TEMPORAL_MISS",
    "CONFLICT_MISS",
    "PROVENANCE_MISS",
    "INSUFFICIENT_EVIDENCE",
    "ANSWER_GENERATION_MISS",
    "SAFE_ABSTENTION",
    "INFRASTRUCTURE_ERROR",
)

_ABSTENTION_MARKERS = ("unknown", "abstain", "not found", "cannot determine", "no information")


def _abstains(answer: str) -> bool:
    return any(m in answer.lower() for m in _ABSTENTION_MARKERS)


def classify_result(
    result: dict[str, Any],
    *,
    question: dict[str, Any] | None = None,
    context: Any | None = None,
) -> str:
    """Classify one pipeline result into a single category.

    `context` is the decomposed QueryContext when available; without it the
    classifier falls back to the result's own layer diagnostics.
    """
    if result.get("error"):
        return "INFRASTRUCTURE_ERROR"

    state = result.get("state_result") or {}
    status = state.get("status")
    answer = str(result.get("answer") or "").strip()
    layers = result.get("layers") or {}
    resolution = state.get("resolution")

    intent = None
    if context is not None:
        intent = getattr(context, "intent", None)
    if intent is None and question:
        from .decompose import classify_intent

        intent = classify_intent(str(question.get("question", "")))

    retrieved = (result.get("resolved_entities") or []) or (layers.get("retrieval") or {}).get("artifacts", 0)

    if intent == "ENTITY_RESOLUTION":
        pair = (layers.get("entity_resolution") or {}).get("pair_verdict")
        if pair == "uncertain":
            return "ENTITY_RESOLUTION_MISS"
        return "OK" if pair else "ENTITY_RESOLUTION_MISS"

    if intent == "PROVENANCE":
        if not result.get("evidence"):
            return "PROVENANCE_MISS" if retrieved else "RETRIEVAL_MISS"
        return "OK" if answer else "ANSWER_GENERATION_MISS"

    if status in ("conflict", "review"):
        return "CONFLICT_MISS"

    if status == "absent":
        if not retrieved:
            return "RETRIEVAL_MISS"
        if resolution == "historical-previous" or any(
            c.kind in ("before", "after", "as_of", "historical")
            for c in (getattr(context, "temporal", []) if context else [])
        ):
            return "TEMPORAL_MISS"
        return "INSUFFICIENT_EVIDENCE"

    if status == "definitive":
        if not answer:
            return "ANSWER_GENERATION_MISS"
        if _abstains(answer):
            return "SAFE_ABSTENTION"
        return "OK"

    return "INSUFFICIENT_EVIDENCE"


def summarize(rows: list[dict[str, Any]], questions_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Aggregate classification across many results."""
    counts: dict[str, int] = {}
    examples: list[dict[str, Any]] = []
    for row in rows:
        qid = str(row.get("question_id", ""))
        category = classify_result(row, question=questions_by_id.get(qid))
        counts[category] = counts.get(category, 0) + 1
        if len(examples) < 40:
            examples.append({"question_id": qid, "category": category})
    return {"summary": counts, "examples": examples}