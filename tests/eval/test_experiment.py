"""Experiment runner tests."""

import json
from pathlib import Path

import pytest

from continuum.eval.experiment import run_dir, run_extraction_eval

ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = ROOT / "data" / "ground_truth" / "v1"


@pytest.mark.skipif(not (GOLD_ROOT / "manifest.json").exists(), reason="gold benchmark not built")
def test_run_extraction_eval_writes_required_metadata(tmp_path):
    report = run_extraction_eval(
        run_id="test_001",
        strategy="deterministic",
        gold_root=GOLD_ROOT,
        eval_root=tmp_path,
        write_predictions=False,
    )
    out = run_dir(tmp_path, "test_001")
    assert (out / "config.json").exists()
    assert (out / "metrics.json").exists()
    assert (out / "report.json").exists()

    config = json.loads((out / "config.json").read_text(encoding="utf-8"))
    for key in ("run_id", "strategy", "dataset_version", "commit_sha", "prompt_version"):
        assert key in config

    assert "mention" in report["metrics"]
    assert "claim_abstention" in report["metrics"]
    assert "failure_summary" in report
