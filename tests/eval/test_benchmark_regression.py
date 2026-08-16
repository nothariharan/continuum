"""Regression slice benchmark tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from continuum.eval.benchmark.runner import run_benchmark
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, load_questions


@pytest.fixture(scope="module")
def require_regression_built():
    path = DEFAULT_BENCHMARK_ROOT / "sample-v1" / "regression" / "questions.jsonl"
    if not path.exists():
        pytest.skip("run build_benchmark_v1 first")


def test_regression_slice_size(require_regression_built):
    rows = load_questions("sample-v1", regression=True)
    assert 8 <= len(rows) <= 10


def test_regression_mock_run(require_regression_built):
    comparison = run_benchmark("sample-v1", answer_model="mock", regression=True)
    assert comparison["question_count"] == len(load_questions("sample-v1", regression=True))
