"""Official benchmark scoring and Continuum diagnostics."""

from __future__ import annotations

import re
from statistics import mean
from typing import Any


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


ABSTENTION_MARKERS = (
    "abstain",
    "not found",
    "unknown",
    "cannot determine",
    "no information",
    "info not found",
)


def _is_abstention(text: str) -> bool:
    return any(marker in text for marker in ABSTENTION_MARKERS)


def score_answer_v1(got: str, gold: str) -> bool:
    """Legacy scorer (pre-versioning). Preserved verbatim for reproducing old
    benchmark numbers. Known bug: an empty `got` passes the substring check
    (`"" in gold_n` is True), so `score_answer_v1("", gold) == True`."""
    got_n = normalize_text(got)
    gold_n = normalize_text(gold)
    if not gold_n:
        return False
    if got_n == gold_n:
        return True
    if gold_n in got_n or got_n in gold_n:
        return True
    if _is_abstention(gold_n) and _is_abstention(got_n):
        return True
    gold_tokens = set(gold_n.split())
    got_tokens = set(got_n.split())
    if len(gold_tokens) >= 3:
        overlap = len(gold_tokens & got_tokens) / len(gold_tokens)
        if overlap >= 0.6:
            return True
    return False


def score_answer_v2(got: str, gold: str) -> bool:
    """Current official scorer.

    Differences vs v1:
    - rejects empty/whitespace `got` up front (v1 let `"" in gold` pass);
    - requires a minimum informative answer (empty and 1-char answers never
      pass);
    - everything else (exact, substring, abstention symmetry, token overlap)
      is unchanged.
    """
    got_n = normalize_text(got)
    gold_n = normalize_text(gold)
    if not got_n or not gold_n:
        return False
    if len(got_n) < 2:
        return False
    if got_n == gold_n:
        return True
    if gold_n in got_n or got_n in gold_n:
        return True
    if _is_abstention(gold_n) and _is_abstention(got_n):
        return True
    gold_tokens = set(gold_n.split())
    got_tokens = set(got_n.split())
    if len(gold_tokens) >= 3:
        overlap = len(gold_tokens & got_tokens) / len(gold_tokens)
        if overlap >= 0.6:
            return True
    return False


# Backward-compatible alias: analysis/audit scripts that reproduce the OLD
# number keep importing `score_answer` (== v1). The official leaderboard uses
# `score_rows`, which is versioned to v2.
score_answer = score_answer_v1


def score_document_recall(retrieved_ids: list[str], expected_ids: list[str]) -> float | None:
    expected = set(expected_ids or ())
    if not expected:
        return None
    retrieved = set(retrieved_ids or ())
    return len(expected & retrieved) / len(expected)


def score_invalid_extra_evidence(retrieved_ids: list[str], expected_ids: list[str]) -> float | None:
    expected = set(expected_ids or ())
    if not expected:
        return None
    retrieved = set(retrieved_ids or ())
    extra = retrieved - expected
    return float(len(extra))


def score_rows(rows: list[dict[str, Any]], questions_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    answer_correct = 0
    recall_values: list[float] = []
    extra_values: list[float] = []
    for row in rows:
        question = questions_by_id[row["question_id"]]
        expected_ids = question.get("expected_doc_ids") or []
        if score_answer_v2(str(row.get("answer", "")), str(question.get("gold_answer", ""))):
            answer_correct += 1
        recall = score_document_recall(row.get("retrieved_artifacts") or [], expected_ids)
        if recall is not None:
            recall_values.append(recall)
        extra = score_invalid_extra_evidence(row.get("retrieved_artifacts") or [], expected_ids)
        if extra is not None:
            extra_values.append(extra)

    total = max(len(rows), 1)
    return {
        "answer_correctness": round(answer_correct / total, 4),
        "document_recall_mean": round(mean(recall_values), 4) if recall_values else None,
        "invalid_extra_evidence_mean": round(mean(extra_values), 4) if extra_values else None,
        "question_count": len(rows),
    }


def aggregate_official_scores(
    system_reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        system: report.get("official_score", {})
        for system, report in system_reports.items()
    }


def aggregate_latency(system_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for system, report in system_reports.items():
        out[system] = report.get("latency", {})
    return out


def aggregate_context_efficiency(system_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for system, report in system_reports.items():
        out[system] = report.get("context_efficiency", {})
    return out


def summarize_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"artifact_count_mean": 0, "context_chars_mean": 0, "context_tokens_mean": 0}
    return {
        "artifact_count_mean": round(mean(len(r.get("retrieved_artifacts") or []) for r in rows), 2),
        "context_chars_mean": round(mean(r.get("context_chars") or 0 for r in rows), 2),
        "context_tokens_mean": round(mean(r.get("context_tokens") or 0 for r in rows), 2),
        "evidence_items_mean": round(mean(r.get("evidence_items") or 0 for r in rows), 2),
    }


def summarize_latency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = sorted(r.get("latency_ms") or 0 for r in rows)
    if not totals:
        return {"p50": 0, "p95": 0, "mean": 0}
    p50 = totals[len(totals) // 2]
    p95 = totals[max(int(len(totals) * 0.95) - 1, 0)]
    return {"p50": round(p50, 2), "p95": round(p95, 2), "mean": round(mean(totals), 2)}


def summarize_stage_latency(rows: list[dict[str, Any]]) -> dict[str, float]:
    keys = ("retrieval_ms", "entity_ms", "graph_ms", "state_ms", "generation_ms")
    out: dict[str, float] = {}
    for key in keys:
        values = [float((r.get("latency_breakdown") or {}).get(key) or 0) for r in rows]
        out[key] = round(mean(values), 2) if values else 0.0
    return out
