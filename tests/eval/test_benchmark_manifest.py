"""Benchmark manifest and question set tests."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from continuum.eval.benchmark.schema import (
    DEFAULT_BENCHMARK_ROOT,
    load_manifest,
    load_questions,
    validate_question_row,
)

SAMPLE_ROOT = DEFAULT_BENCHMARK_ROOT / "sample-v1"
FULL_ROOT = DEFAULT_BENCHMARK_ROOT / "full-v1"


@pytest.fixture(scope="module")
def require_sample_built():
    if not (SAMPLE_ROOT / "manifest.json").exists():
        pytest.skip("run build_benchmark_v1 first")


@pytest.fixture(scope="module")
def require_full_built():
    if not (FULL_ROOT / "manifest.json").exists():
        pytest.skip("run build_benchmark_v1 first")


def test_sample_manifest_dev_only(require_sample_built):
    manifest = load_manifest("sample-v1")
    assert manifest.corpus_mode == "sample-v1"
    assert manifest.official_benchmark is False
    assert 50 <= manifest.question_count <= 100


def test_full_manifest_official(require_full_built):
    manifest = load_manifest("full-v1")
    assert manifest.corpus_mode == "full-v1"
    assert manifest.official_benchmark is True
    assert manifest.question_count == 500


def test_question_rows_valid(require_sample_built, require_full_built):
    for mode in ("sample-v1", "full-v1"):
        for row in load_questions(mode):
            assert not validate_question_row(row), row.get("question_id")


def test_sample_has_type_coverage(require_sample_built):
    types = Counter(row["question_type"] for row in load_questions("sample-v1"))
    assert len(types) >= 5
