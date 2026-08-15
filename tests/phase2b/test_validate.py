"""Validation tests for Phase 2B extraction outputs."""

from pathlib import Path

from continuum.eval.validate import validate_extraction_outputs

ROOT = Path(__file__).resolve().parents[2]


def test_validate_committed_extraction_outputs():
    report = validate_extraction_outputs(
        sample_path=ROOT / "data/samples/phase2a-sample.jsonl",
        mentions_path=ROOT / "data/extraction/mentions.jsonl",
        claims_path=ROOT / "data/extraction/claims.jsonl",
    )
    assert report.sample_artifact_count == 360
    assert report.mention_rows > 0
    assert report.claim_rows > 0
    assert not report.orphan_artifact_ids
    assert report.ok, report.errors[:5]
