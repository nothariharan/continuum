"""End-to-end mock benchmark run tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from continuum.eval.benchmark.runner import run_benchmark
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, SYSTEMS, validate_result_row


@pytest.fixture(scope="module")
def require_sample_built():
    if not (DEFAULT_BENCHMARK_ROOT / "sample-v1" / "questions.jsonl").exists():
        pytest.skip("run build_benchmark_v1 first")


def test_mock_run_produces_all_system_reports(require_sample_built):
    comparison = run_benchmark("sample-v1", answer_model="mock")
    reports_dir = DEFAULT_BENCHMARK_ROOT / "reports" / "sample-v1"
    assert comparison["official_benchmark"] is False
    assert set(comparison["official_score"]) == set(SYSTEMS)
    for system in SYSTEMS:
        report = json.loads((reports_dir / f"{system}.json").read_text(encoding="utf-8"))
        assert report["rows"], system
        for row in report["rows"]:
            assert not validate_result_row(row)
    comparison_path = reports_dir / "comparison.json"
    assert comparison_path.exists()
    payload = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert "continuum_diagnostics" in payload
    assert "official_score" in payload
