"""Schema round-trip tests for Phase 2B extraction contract."""

from continuum.extract.schemas import Claim, Mention, claim_to_dict, mention_to_dict


def test_mention_schema_round_trip():
    mention = Mention.create(
        artifact_id="dsid_abc123",
        source="gmail",
        raw_text="Sarah Chen",
        type="person",
        content="From: Sarah Chen <sarah@example.com>",
        span_start=6,
        span_end=16,
        source_identity="sarah@example.com",
        confidence=0.95,
    )
    data = mention_to_dict(mention)
    assert data["artifact_id"] == "dsid_abc123"
    assert data["raw_text"] == "Sarah Chen"
    assert data["type"] == "person"
    assert data["confidence"] == 0.95
    assert data["mention_id"]


def test_claim_schema_round_trip():
    claim = Claim.create(
        artifact_id="dsid_abc123",
        subject_mention="Sarah Chen",
        predicate="OWNS",
        object_mention="Acme",
        observed_at="2026-07-28T00:00:00",
        evidence_span="Sarah is taking over Acme from Arjun",
        confidence=0.85,
    )
    data = claim_to_dict(claim)
    assert data["predicate"] == "OWNS"
    assert data["subject_mention"] == "Sarah Chen"
    assert data["valid_to"] is None
    assert data["claim_id"]
