"""Evaluation metric tests."""

from continuum.eval.metrics import score_claims, score_mentions
from continuum.extract.schemas import Claim, Mention, normalize_mention_text


def test_normalize_mention_text():
    assert normalize_mention_text("@Soham") == "soham"


def test_mention_precision_recall():
    gold = [{"raw_text": "Sarah Chen", "type": "person"}]
    predicted = [
        Mention.create(
            artifact_id="dsid_x",
            source="gmail",
            raw_text="Sarah Chen",
            type="person",
            content="Sarah Chen owns Acme",
            span_start=0,
            span_end=10,
        ),
        Mention.create(
            artifact_id="dsid_x",
            source="gmail",
            raw_text="Extra Person",
            type="person",
            content="Extra Person mentioned",
            span_start=0,
            span_end=12,
        ),
    ]
    scores = score_mentions(predicted, gold, artifact_id="dsid_x")
    assert scores["tp"] == 1
    assert scores["fp"] == 1
    assert scores["precision"] == 0.5
    assert scores["recall"] == 1.0


def test_claim_precision_recall():
    gold = [{"subject_mention": "Sarah", "predicate": "OWNS", "object_mention": "Acme"}]
    predicted = [
        Claim.create(
            artifact_id="dsid_x",
            subject_mention="Sarah",
            predicate="OWNS",
            object_mention="Acme",
            observed_at="2026-07-28",
            evidence_span="Sarah owns Acme",
        )
    ]
    scores = score_claims(predicted, gold, artifact_id="dsid_x")
    assert scores["precision"] == 1.0
    assert scores["recall"] == 1.0
