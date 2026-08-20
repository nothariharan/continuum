"""Stratified question selection for sample-v1, subset-20pct, and full-v1."""

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

DEFAULT_SUBSET_SEED = 42
DEFAULT_SUBSET_SIZE = 100
DEFAULT_DEV_SIZE = 80


def select_full_v1(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(questions)


def proportional_quotas(total: int, category_counts: dict[str, int]) -> dict[str, int]:
    """Allocate `total` items proportionally across non-empty categories."""
    grand = sum(category_counts.values())
    if grand <= 0 or total <= 0:
        return {}

    quotas: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    allocated = 0
    for qtype, count in category_counts.items():
        if count <= 0:
            continue
        exact = total * count / grand
        base = int(exact)
        quotas[qtype] = base
        allocated += base
        remainders.append((exact - base, qtype))

    remainders.sort(key=lambda item: item[0], reverse=True)
    index = 0
    while allocated < total and remainders:
        qtype = remainders[index % len(remainders)][1]
        quotas[qtype] = quotas.get(qtype, 0) + 1
        allocated += 1
        index += 1
    return quotas


def select_proportional_subset(
    questions: list[dict[str, Any]],
    *,
    target: int = DEFAULT_SUBSET_SIZE,
    seed: int = DEFAULT_SUBSET_SEED,
) -> list[dict[str, Any]]:
    """Proportional stratified sample by official question_type."""
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        by_type[str(question.get("question_type", "miscellaneous"))].append(question)

    category_counts = {
        qtype: len(by_type[qtype])
        for qtype in OFFICIAL_TYPES
        if by_type.get(qtype)
    }
    quotas = proportional_quotas(target, category_counts)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    for qtype in OFFICIAL_TYPES:
        pool = by_type.get(qtype, [])
        if not pool:
            continue
        rng.shuffle(pool)
        take = min(quotas.get(qtype, 0), len(pool))
        selected.extend(pool[:take])

    selected.sort(key=lambda q: str(q["question_id"]))
    return selected[:target]


def select_dev_holdout_split(
    question_ids: list[str],
    *,
    dev_size: int = DEFAULT_DEV_SIZE,
    seed: int = DEFAULT_SUBSET_SEED,
) -> tuple[list[str], list[str]]:
    """Split question IDs into dev and holdout sets deterministically."""
    rng = random.Random(seed + 1)
    ids = list(question_ids)
    rng.shuffle(ids)
    dev = sorted(ids[:dev_size])
    holdout = sorted(ids[dev_size:])
    return dev, holdout


def category_counts(questions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for question in questions:
        counts[str(question.get("question_type", "miscellaneous"))] += 1
    return dict(sorted(counts.items()))


def select_sample_v1(
    questions: list[dict[str, Any]],
    *,
    target: int = 75,
    seed: int = 20260816,
) -> list[dict[str, Any]]:
    """Stratified dev slice across official question_type values (round-robin)."""
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
