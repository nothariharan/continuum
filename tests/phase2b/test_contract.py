"""Unit tests for the shared contract: schema validation, JSONL IO, resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from continuum.claims import ContractError, load_claims, validate_claim, validate_mention
from continuum.hydradb.claims import _contradiction_pairs, _validity_overlap, resolve_mentions

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "data" / "fixtures" / "phase2b"


def valid_claim() -> dict:
    return {
        "claim_id": "claim:test-1",
        "artifact_id": "artifact:test-artifact",
        "subject_mention": "Ava Nguyen",
        "predicate": "OWNS",
        "object_mention": "CedarBank",
        "observed_at": "2026-06-01",
        "valid_from": "2026-06-01",
        "valid_to": None,
        "confidence": 0.9,
        "extraction_method": "hand-written",
    }


def test_claim_contract_round_trip():
    claim = validate_claim(valid_claim())
    assert claim.claim_id == "claim:test-1"
    assert claim.subject_mention == "Ava Nguyen"
    assert claim.valid_to is None
    assert claim.to_dict()["predicate"] == "OWNS"


@pytest.mark.parametrize(
    "field,value",
    [
        ("claim_id", "not-a-claim-id"),
        ("artifact_id", "bogus"),
        ("subject_mention", ""),
        ("predicate", "owns"),
        ("object_mention", "  "),
        ("observed_at", "June 2026"),
        ("valid_from", "2026-06-32"),
        ("valid_to", "not-a-date"),
        ("confidence", 1.5),
        ("confidence", "high"),
        ("extraction_method", ""),
    ],
)
def test_claim_rejects_invalid_fields(field, value):
    record = valid_claim()
    record[field] = value
    with pytest.raises(ContractError):
        validate_claim(record)


def test_claim_rejects_valid_to_before_valid_from():
    record = valid_claim()
    record["valid_from"] = "2026-06-10"
    record["valid_to"] = "2026-06-01"
    with pytest.raises(ContractError):
        validate_claim(record)


def test_mention_contract():
    mention = validate_mention(
        {
            "mention_id": "mention:test-1",
            "artifact_id": "artifact:test-artifact",
            "text": "Ava",
            "mention_type": "PERSON",
            "span_start": 3,
            "span_end": 6,
        }
    )
    assert mention.mention_type == "PERSON"
    with pytest.raises(ContractError):
        validate_mention(
            {
                "mention_id": "mention:test-2",
                "artifact_id": "artifact:test-artifact",
                "text": "x",
                "mention_type": "UNKNOWN_TYPE",
            }
        )
    with pytest.raises(ContractError):
        validate_mention(
            {
                "mention_id": "mention:test-3",
                "artifact_id": "artifact:test-artifact",
                "text": "x",
                "mention_type": "PERSON",
                "span_start": 5,
                "span_end": 5,
            }
        )


def test_fixture_claims_are_contract_valid():
    claims = load_claims(FIXTURE / "claims.jsonl")
    assert len(claims) == 9
    assert len({claim.claim_id for claim in claims}) == 9


def test_fixture_resolution_covers_all_mentions():
    claims = load_claims(FIXTURE / "claims.jsonl")
    resolutions = json.loads((FIXTURE / "resolutions.json").read_text(encoding="utf-8"))
    resolved = resolve_mentions(claims, resolutions)
    for claim in claims:
        assert claim.subject_mention in resolved
        assert claim.object_mention in resolved


def test_contradiction_derivation():
    claims = load_claims(FIXTURE / "claims.jsonl")
    resolutions = json.loads((FIXTURE / "resolutions.json").read_text(encoding="utf-8"))
    entities = resolve_mentions(claims, resolutions)
    resolved = [
        {
            "claim_id": claim.claim_id,
            "predicate": claim.predicate,
            "subject_id": entities[claim.subject_mention]["key"],
            "object_id": entities[claim.object_mention]["key"],
            "valid_from": claim.valid_from[:10],
            "valid_to": claim.valid_to[:10] if claim.valid_to else None,
        }
        for claim in claims
    ]
    pairs = _contradiction_pairs(resolved)
    assert pairs == [
        ("claim:may-owns-cedarbank", "claim:camila-takes-cedarbank"),
        ("claim:may-owns-cedarbank", "claim:camila-owns-cedarbank"),
    ]


def test_validity_overlap_semantics():
    a = {"valid_from": "2026-05-01", "valid_to": None}
    b = {"valid_from": "2026-06-20", "valid_to": None}
    c = {"valid_from": "2026-08-01", "valid_to": "2026-08-31"}
    d = {"valid_from": "2026-09-01", "valid_to": None}
    assert _validity_overlap(a, b)
    assert _validity_overlap(a, c)
    assert _validity_overlap(c, b)
    assert not _validity_overlap(c, d)
