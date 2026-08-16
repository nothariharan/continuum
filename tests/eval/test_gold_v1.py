"""Gold Benchmark v1 tests."""

from pathlib import Path

import pytest

from continuum.eval.gold_v1 import (
    GoldAmbiguityRow,
    GoldBenchmark,
    GoldClaimRow,
    GoldMentionRow,
    build_gold_benchmark,
    validate_gold_benchmark,
)
from continuum.eval.metrics import score_gold_claims_abstention

ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = ROOT / "data" / "ground_truth" / "v1"


def test_build_gold_benchmark_covers_all_sources():
    benchmark = build_gold_benchmark(count=150, seed=20260816)
    errors = validate_gold_benchmark(benchmark)
    assert not errors, errors
    assert len(benchmark.artifacts) == 150
    assert len(benchmark.manifest["source_coverage"]) == 9


def test_committed_gold_benchmark_valid():
    if not (GOLD_ROOT / "manifest.json").exists():
        pytest.skip("gold benchmark not built yet")
    from continuum.eval.gold_v1 import load_gold_benchmark

    benchmark = load_gold_benchmark(GOLD_ROOT)
    errors = validate_gold_benchmark(benchmark)
    assert not errors, errors


def test_abstention_scoring_no_claim():
    benchmark = GoldBenchmark(
        manifest={"version": "v1", "source_coverage": {}},
        artifacts=[{"id": "dsid_a", "source": "slack", "content": "hello"}],
        mentions=[],
        claims=[],
        ambiguities=[
            GoldAmbiguityRow(artifact_id="dsid_a", status="NO_CLAIM", notes="none"),
        ],
    )
    from continuum.extract.schemas import Claim

    scores = score_gold_claims_abstention([], benchmark)
    assert scores["tn"] == 1
    assert scores["fp"] == 0

    predicted = [
        Claim.create(
            artifact_id="dsid_a",
            subject_mention="Alice",
            predicate="OWNS",
            object_mention="Acme",
            observed_at="2026-01-01",
            evidence_span="Alice owns Acme",
        )
    ]
    scores = score_gold_claims_abstention(predicted, benchmark)
    assert scores["fp"] == 1
    assert scores["tn"] == 0


def test_abstention_scoring_valid_claim():
    benchmark = GoldBenchmark(
        manifest={"version": "v1", "source_coverage": {}},
        artifacts=[{"id": "dsid_b", "source": "gmail", "content": "Sarah owns Acme"}],
        mentions=[],
        claims=[
            GoldClaimRow(
                artifact_id="dsid_b",
                subject="Sarah",
                subject_type="person",
                predicate="OWNS",
                object="Acme",
                object_type="account",
                evidence_span="Sarah owns Acme",
                observed_at="2026-01-01",
                valid_from=None,
                valid_to=None,
                status="VALID",
            )
        ],
        ambiguities=[],
    )
    from continuum.extract.schemas import Claim

    predicted = [
        Claim.create(
            artifact_id="dsid_b",
            subject_mention="Sarah",
            predicate="OWNS",
            object_mention="Acme",
            observed_at="2026-01-01",
            evidence_span="Sarah owns Acme",
        )
    ]
    scores = score_gold_claims_abstention(predicted, benchmark)
    assert scores["tp"] == 1
    assert scores["fp"] == 0
    assert scores["fn"] == 0
