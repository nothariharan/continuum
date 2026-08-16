"""End-to-end question benchmark tests — the full vertical, smoke level."""

from __future__ import annotations

import json

import pytest

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def test_eval_questions_fixture_is_wellformed():
    rows = [json.loads(line) for line in (ROOT / "data" / "labels" / "eval-questions.jsonl").open(encoding="utf-8") if line.strip()]
    assert len(rows) == 20
    for row in rows:
        assert row["question_id"]
        assert row["question"]
        assert row["category"]
        assert "expected_answer" in row


def test_eval_questions_cover_categories():
    rows = [json.loads(line) for line in (ROOT / "data" / "labels" / "eval-questions.jsonl").open(encoding="utf-8") if line.strip()]
    categories = {row["category"] for row in rows}
    assert {"single-hop", "multi-hop", "temporal", "conflict", "abstention", "provenance", "entity-resolution"} <= categories


@pytest.mark.hydradb
def test_e2e_benchmark_runs_and_passes(client):
    """End-to-end: every question must be answerable with the real fixture."""
    import subprocess
    import sys

    # Real-claims mode requires the dsid_* artifacts to be in the graph;
    # load the 360-artifact sample first (mirrors eval_real_claims.py).
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "dataset_load_hydradb.py"), "--reset"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        [
            sys.executable, str(ROOT / "scripts" / "load_phase2b_claims.py"), "--reset", "--real",
            "--claims", str(ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"),
            "--resolutions", str(ROOT / "data" / "fixtures" / "phase2b" / "resolutions-real.json"),
        ],
        check=True, capture_output=True, text=True,
    )
    sys.path.insert(0, str(ROOT / "scripts"))
    import benchmark_e2e_questions as bench

    report = bench.main(ROOT / "data" / "labels" / "eval-questions.jsonl", ROOT / "data" / "metadata" / "e2e_question_benchmark_test.json")
    assert report["accuracy"] >= 0.90, f"e2e accuracy too low: {report['accuracy']}"
    assert report["questions"] == 20

    report = bench.main(ROOT / "data" / "labels" / "eval-questions.jsonl", ROOT / "data" / "metadata" / "e2e_question_benchmark_test.json")
    assert report["accuracy"] >= 0.90, f"e2e accuracy too low: {report['accuracy']}"
    assert report["questions"] == 20
