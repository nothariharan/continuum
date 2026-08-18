"""Predicate refinement unit tests — provider protocol, validation, abstention."""

from __future__ import annotations

from continuum.extract.v2.pipeline import _allowed_predicates, refine_ambiguous_claims
from continuum.extract.v2.refinement import (
    ABSTAIN,
    MockPredicateProvider,
    validate_refinement,
)

LEXICON = {
    "person:sarah": {
        "name": "Sarah Chen", "label": "Person",
        "mentions": ["Sarah Chen", "Sarah"], "aliases": ["sarah_csm"],
    },
    "account:acme": {
        "name": "ACME", "label": "Account",
        "mentions": ["ACME"], "aliases": ["acme"],
    },
}


def _claim(predicate: str = "OWNS", ambiguous: bool = True, **overrides) -> dict:
    claim = {
        "claim_id": "aabbccddeeff0011",
        "artifact_id": "dsid_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "subject_mention": "Sarah Chen",
        "predicate": predicate,
        "object_mention": "ACME",
        "observed_at": "2026-07-29T00:00:00",
        "valid_from": None,
        "valid_to": None,
        "confidence": 0.8,
        "extraction_method": "deterministic-v2",
        "evidence_span": "Owner: Sarah Chen -",
        "metadata": {
            "v2": True,
            "subject_key": "person:sarah",
            "object_key": "account:acme",
            "subject_label": "Person",
            "object_label": "Account",
            "signal": "email-thread",
            "ambiguous": ambiguous,
            "candidate_predicate": predicate,
        },
    }
    claim.update(overrides)
    return claim


def test_allowed_predicates_person_account():
    allowed = _allowed_predicates("Person", "Account", "OWNS")
    assert allowed == {"OWNS", "MAINTAINS", "LEADS", "ASSIGNED_TO"}


def test_allowed_predicates_never_reviews_for_thread():
    allowed = _allowed_predicates("Person", "Account", "OWNS")
    assert "REVIEWS" not in allowed


def test_allowed_predicates_unknown_labels_fallback():
    allowed = _allowed_predicates("person", "account", "OWNS")
    assert allowed == {"OWNS"}


def test_mock_provider_keeps_candidate():
    result = MockPredicateProvider().refine(
        {"candidate_predicate": "OWNS", "candidate_confidence": 0.7}
    )
    assert result.predicate == "OWNS"
    assert result.confidence == 0.7
    assert not result.abstained


def test_validate_refinement_strict_enum():
    assert validate_refinement({"predicate": "LEADS", "confidence": 0.9})["predicate"] == "LEADS"
    assert validate_refinement({"predicate": "NOT_A_PRED", "confidence": 0.9})["predicate"] == ABSTAIN
    assert validate_refinement({"predicate": "owls", "confidence": 0.9})["predicate"] == ABSTAIN


def test_validate_refinement_confidence_range():
    assert validate_refinement({"predicate": "OWNS", "confidence": 1.5})["confidence"] == 0.0
    assert validate_refinement({"predicate": "OWNS", "confidence": "nope"})["confidence"] == 0.0


def test_validate_refinement_rejects_non_dict():
    assert not validate_refinement(None)["valid"]
    assert not validate_refinement(["OWNS"])["valid"]


def test_ambiguous_only_mode_skips_clear_claims():
    clear = _claim(ambiguous=False)
    result = refine_ambiguous_claims([clear], MockPredicateProvider(), LEXICON, mode="ambiguous")
    assert result["calls"] == 0
    assert result["claims"][0]["predicate"] == "OWNS"


def test_ambiguous_mode_refines_only_ambiguous():
    clear = _claim(ambiguous=False)
    ambig = _claim(ambiguous=True, claim_id="aabbccddeeff0022")
    result = refine_ambiguous_claims([clear, ambig], MockPredicateProvider(), LEXICON, mode="ambiguous")
    assert result["calls"] == 1
    assert result["claims"][0] is clear or result["claims"][0]["claim_id"] == clear["claim_id"]


def test_all_mode_refines_everything():
    clear = _claim(ambiguous=False)
    result = refine_ambiguous_claims([clear], MockPredicateProvider(), LEXICON, mode="all")
    assert result["calls"] == 1


def test_refinement_rewrites_predicate_and_rehash():
    class FixedProvider:
        def refine(self, context):
            from continuum.extract.v2.refinement import RefinementResult

            return RefinementResult(predicate="MAINTAINS", confidence=0.85, provider="fixed")

    claim = _claim(ambiguous=True)
    result = refine_ambiguous_claims([claim], FixedProvider(), LEXICON, mode="ambiguous")
    assert result["refined"] == 1
    final = result["claims"][0]
    assert final["predicate"] == "MAINTAINS"
    assert final["claim_id"] != claim["claim_id"]
    assert final["metadata"]["refined_from"] == "OWNS"


def test_abstention_keeps_candidate():
    class AbstainProvider:
        def refine(self, context):
            from continuum.extract.v2.refinement import RefinementResult

            return RefinementResult(predicate=ABSTAIN, confidence=0.0, provider="abstainer")

    claim = _claim(ambiguous=True)
    result = refine_ambiguous_claims([claim], AbstainProvider(), LEXICON, mode="ambiguous")
    assert result["abstained"] == 1
    assert result["claims"][0]["predicate"] == "OWNS"


def test_claims_metadata_has_labels():
    claim = _claim()
    assert claim["metadata"]["subject_label"] == "Person"
    assert claim["metadata"]["object_label"] == "Account"


def test_malformed_json_abstains():
    assert validate_refinement({"predicate": "INVENTED", "confidence": 0.9})["predicate"] == ABSTAIN
    assert validate_refinement("not json")["predicate"] == ABSTAIN


def test_create_refinement_provider_falls_back_without_key(monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from continuum.extract.v2.refinement import MockPredicateProvider, create_refinement_provider

    provider = create_refinement_provider("auto")
    assert isinstance(provider, MockPredicateProvider)
