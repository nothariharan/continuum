"""ER-Bench failure taxonomy for baseline analysis."""

from __future__ import annotations

from typing import Any

CONTINUUM_CATEGORIES = (
    "RETRIEVAL_FAILURE",
    "ENTITY_RESOLUTION_FAILURE",
    "CLAIM_EXTRACTION_FAILURE",
    "TEMPORAL_STATE_FAILURE",
    "CONFLICT_RESOLUTION_FAILURE",
    "ABSTENTION_FAILURE",
    "PROVENANCE_FAILURE",
    "ANSWER_GENERATION_FAILURE",
    "PARSER_FAILURE",
    "INFRASTRUCTURE_FAILURE",
)

RAG_CATEGORIES = (
    "RETRIEVAL_FAILURE",
    "CONTEXT_OMISSION",
    "CONTEXT_NOISE",
    "ANSWER_GENERATION_FAILURE",
    "ABSTENTION_FAILURE",
    "PARSER_FAILURE",
    "INFRASTRUCTURE_FAILURE",
)


def _is_abstention_gold(gold: str) -> bool:
    gold_l = (gold or "").lower()
    return any(m in gold_l for m in ("not found", "unknown", "no information", "cannot determine"))


def classify_row(row: dict[str, Any], question: dict[str, Any]) -> str:
    if row.get("error"):
        return "INFRASTRUCTURE_FAILURE"

    system = row.get("system", "")
    gold = str(question.get("gold_answer", ""))
    answer = str(row.get("answer", ""))
    expected_ids = set(question.get("expected_doc_ids") or ())
    retrieved = set(row.get("retrieved_artifacts") or ())

    if system == "continuum":
        coverage = row.get("graph_coverage") or {}
        if coverage.get("graph_abstain") and not _is_abstention_gold(gold):
            if not retrieved and not expected_ids:
                return "ABSTENTION_FAILURE"
            if not coverage.get("graph_state_hit"):
                return "ENTITY_RESOLUTION_FAILURE"
        state = row.get("state_result") or {}
        if isinstance(state, dict) and state.get("status") == "conflict" and "conflict" not in answer.lower():
            return "CONFLICT_RESOLUTION_FAILURE"
        if expected_ids and not (expected_ids & retrieved):
            return "RETRIEVAL_FAILURE"
        if _is_abstention_gold(gold) and answer and "abstain" not in answer.lower() and answer.lower() != "unknown":
            return "ABSTENTION_FAILURE"
        if not answer.strip():
            return "ANSWER_GENERATION_FAILURE"
        return "ANSWER_GENERATION_FAILURE"

    if not retrieved:
        return "RETRIEVAL_FAILURE"
    if expected_ids and not (expected_ids & retrieved):
        return "RETRIEVAL_FAILURE"
    extra = retrieved - expected_ids
    if expected_ids and len(extra) > len(expected_ids):
        return "CONTEXT_NOISE"
    if _is_abstention_gold(gold) and "not found" not in answer.lower() and "unknown" not in answer.lower():
        return "ABSTENTION_FAILURE"
    if not answer.strip():
        return "ANSWER_GENERATION_FAILURE"
    return "ANSWER_GENERATION_FAILURE"


def build_failure_analysis(
    rows: list[dict[str, Any]],
    questions_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    summary: dict[str, int] = {}
    by_system: dict[str, dict[str, int]] = {}
    examples: list[dict[str, Any]] = []

    for row in rows:
        qid = str(row["question_id"])
        question = questions_by_id.get(qid, {})
        category = classify_row(row, question)
        summary[category] = summary.get(category, 0) + 1
        system = str(row.get("system", "unknown"))
        by_system.setdefault(system, {})
        by_system[system][category] = by_system[system].get(category, 0) + 1
        if len(examples) < 50:
            examples.append({"question_id": qid, "system": system, "category": category, "error": row.get("error")})

    return {
        "failure_summary": summary,
        "by_system": by_system,
        "examples": examples,
    }
