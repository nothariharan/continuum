"""Tests for proportional subset-20pct selection."""

from __future__ import annotations

from collections import Counter

from continuum.eval.benchmark.questions import load_official_questions
from continuum.eval.benchmark.select import (
    DEFAULT_DEV_SIZE,
    DEFAULT_SUBSET_SEED,
    DEFAULT_SUBSET_SIZE,
    category_counts,
    proportional_quotas,
    select_dev_holdout_split,
    select_proportional_subset,
)


def test_proportional_quotas_sum_to_target():
    counts = {"basic": 175, "semantic": 125, "high_level": 10}
    quotas = proportional_quotas(100, counts)
    assert sum(quotas.values()) == 100
    assert quotas["basic"] == 57
    assert quotas["semantic"] == 40
    assert quotas["high_level"] == 3


def test_select_proportional_subset_is_deterministic():
    official = load_official_questions()
    first = select_proportional_subset(official, target=100, seed=42)
    second = select_proportional_subset(official, target=100, seed=42)
    assert [q["question_id"] for q in first] == [q["question_id"] for q in second]
    assert len(first) == 100


def test_select_proportional_subset_preserves_distribution():
    official = load_official_questions()
    full_counts = category_counts(official)
    selected = select_proportional_subset(official, target=100, seed=DEFAULT_SUBSET_SEED)
    selected_counts = category_counts(selected)
    for qtype, full_count in full_counts.items():
        expected = proportional_quotas(DEFAULT_SUBSET_SIZE, full_counts).get(qtype, 0)
        assert selected_counts.get(qtype, 0) == expected
        assert selected_counts[qtype] / 100 == round(full_count / 500, 2) or abs(
            selected_counts[qtype] / 100 - full_count / 500
        ) < 0.05


def test_dev_holdout_split_is_disjoint():
    official = load_official_questions()
    selected = select_proportional_subset(official, target=DEFAULT_SUBSET_SIZE, seed=DEFAULT_SUBSET_SEED)
    ids = [str(q["question_id"]) for q in selected]
    dev, holdout = select_dev_holdout_split(ids, dev_size=DEFAULT_DEV_SIZE, seed=DEFAULT_SUBSET_SEED)
    assert len(dev) == DEFAULT_DEV_SIZE
    assert len(holdout) == DEFAULT_SUBSET_SIZE - DEFAULT_DEV_SIZE
    assert set(dev).isdisjoint(holdout)
    assert set(dev) | set(holdout) == set(ids)


def test_no_duplicate_question_ids_in_subset():
    official = load_official_questions()
    selected = select_proportional_subset(official, target=100, seed=42)
    ids = [str(q["question_id"]) for q in selected]
    assert len(ids) == len(set(ids))
    assert Counter(category_counts(selected).values()) and sum(category_counts(selected).values()) == 100
