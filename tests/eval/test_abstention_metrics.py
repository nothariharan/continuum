"""Abstention-aware metrics tests."""

from continuum.eval.gold_v1 import GoldAmbiguityRow, GoldBenchmark, GoldClaimRow
from continuum.eval.metrics import score_gold_claims_abstention, score_gold_claims_strict
from continuum.extract.schemas import Claim


def test_ambiguous_artifacts_excluded_from_abstention_score():
    benchmark = GoldBenchmark(
        manifest={"version": "v1", "source_coverage": {}},
        artifacts=[{"id": "dsid_x", "source": "slack", "content": "maybe owns"}],
        mentions=[],
        claims=[
            GoldClaimRow(
                artifact_id="dsid_x",
                subject="Team",
                subject_type="org",
                predicate="OWNS",
                object="Acme",
                object_type="account",
                evidence_span="",
                observed_at=None,
                valid_from=None,
                valid_to=None,
                status="AMBIGUOUS",
            )
        ],
        ambiguities=[
            GoldAmbiguityRow(artifact_id="dsid_x", status="AMBIGUOUS", notes="unclear"),
        ],
    )
    scores = score_gold_claims_abstention([], benchmark)
    assert scores["ambiguous_artifacts_excluded"] == 1
    assert scores["tp"] == 0


def test_strict_vs_abstention_on_valid_gold():
    benchmark = GoldBenchmark(
        manifest={"version": "v1", "source_coverage": {}},
        artifacts=[{"id": "dsid_y", "source": "gmail", "content": "Bob leads Project X"}],
        mentions=[],
        claims=[
            GoldClaimRow(
                artifact_id="dsid_y",
                subject="Bob",
                subject_type="person",
                predicate="LEADS",
                object="Project X",
                object_type="project",
                evidence_span="Bob leads Project X",
                observed_at="2026-02-01",
                valid_from=None,
                valid_to=None,
                status="VALID",
            )
        ],
        ambiguities=[],
    )
    predicted = [
        Claim.create(
            artifact_id="dsid_y",
            subject_mention="Bob",
            predicate="LEADS",
            object_mention="Project X",
            observed_at="2026-02-01",
            evidence_span="Bob leads Project X",
        )
    ]
    strict = score_gold_claims_strict(predicted, benchmark)
    abst = score_gold_claims_abstention(predicted, benchmark)
    assert strict["tp"] == 1
    assert abst["tp"] == 1
