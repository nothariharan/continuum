"""Identity-pair gold dataset v1 tests."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from continuum.eval.identity.schema import (
    DEFAULT_DATASET_PATH,
    FEATURE_SLOTS,
    load_identity_pairs,
    pair_key,
    validate_identity_pairs,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET = DEFAULT_DATASET_PATH


def _rows() -> list[dict]:
    if not DATASET.exists():
        pytest.skip("identity-pairs.jsonl not built yet")
    return load_identity_pairs(DATASET)


def test_schema_validation_on_every_row():
    rows = _rows()
    errors = validate_identity_pairs(rows, require_features=True)
    assert not errors, errors


def test_pair_count_in_range():
    rows = _rows()
    assert 75 <= len(rows) <= 150


def test_all_labels_present():
    rows = _rows()
    labels = {row["label"] for row in rows}
    assert labels == {"SAME_ENTITY", "DIFFERENT_ENTITY", "UNCERTAIN"}


def test_feature_slots_present():
    rows = _rows()
    for row in rows:
        features = row.get("features") or {}
        assert set(features) == set(FEATURE_SLOTS), row["pair_id"]


def test_email_match_coverage_on_email_pairs():
    rows = _rows()
    email_pairs = [
        row
        for row in rows
        if any("email" in tag for tag in row.get("difficulty_tags") or [])
        or row["a"].get("type") == "email"
        or row["b"].get("type") == "email"
        or row["a"].get("emails")
        or row["b"].get("emails")
    ]
    non_null = sum(1 for row in email_pairs if row["features"].get("email_match") is not None)
    assert non_null >= 10, f"email_match non-null on {non_null} email-family pairs"


def test_no_duplicate_mention_pairs():
    rows = _rows()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = pair_key(row["a"]["mention"], row["b"]["mention"])
        assert key not in seen, key
        seen.add(key)


def test_label_mix_targets():
    rows = _rows()
    counts = Counter(row["label"] for row in rows)
    assert counts["SAME_ENTITY"] >= 20
    assert counts["DIFFERENT_ENTITY"] >= 20
    assert counts["UNCERTAIN"] >= 35
