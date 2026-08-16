"""Stratified question selection for sample-v1 and full-v1."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

OFFICIAL_TYPES = (
    "basic",
    "semantic",
    "intra_document_reasoning",
    "project_related",
    "constrained",
    "conflicting_info",
    "completeness",
    "miscellaneous",
    "high_level",
    "info_not_found",
)

REGRESSION_TYPES = (
    "conflicting_info",
    "info_not_found",
    "intra_document_reasoning",
    "completeness",
    "high_level",
)


def select_full_v1(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(questions)


def select_sample_v1(
    questions: list[dict[str, Any]],
    *,
    target: int = 75,
    seed: int = 20260816,
) -> list[dict[str, Any]]:
    """Stratified dev slice across official question_type values."""
    rng = random.Random(seed)
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        by_type[str(question.get("question_type", "miscellaneous"))].append(question)

    types = [t for t in OFFICIAL_TYPES if by_type.get(t)]
    if not types:
        return questions[:target]

    for pool in by_type.values():
        rng.shuffle(pool)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    indices = {qtype: 0 for qtype in types}

    while len(selected) < target:
        progressed = False
        for qtype in types:
            pool = by_type[qtype]
            idx = indices[qtype]
            while idx < len(pool):
                question = pool[idx]
                idx += 1
                qid = str(question["question_id"])
                if qid in seen:
                    continue
                selected.append(question)
                seen.add(qid)
                indices[qtype] = idx
                progressed = True
                break
            else:
                indices[qtype] = idx
            if len(selected) >= target:
                break
        if not progressed:
            break
    return selected[:target]


def select_regression(
    questions: list[dict[str, Any]],
    *,
    limit: int = 10,
    seed: int = 20260816,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    pool = [q for q in questions if q.get("question_type") in REGRESSION_TYPES]
    rng.shuffle(pool)
    if len(pool) >= limit:
        return pool[:limit]
    remaining = [q for q in questions if q not in pool]
    rng.shuffle(remaining)
    return (pool + remaining)[:limit]
