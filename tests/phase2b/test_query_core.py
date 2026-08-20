"""Core-query unit tests — decomposition, temporal, conflict ordering,
failure taxonomy, and fixtures. Pure (no HydraDB required)."""

from __future__ import annotations

from continuum.claims.schema import SUPPORTED_PREDICATES
from continuum.query.conflict import _intervals_disjoint, order_conflicts
from continuum.query.context import QueryContext, TemporalConstraint
from continuum.query.decompose import (
    classify_intent,
    decompose_question,
    extract_entities,
    extract_relationships,
    parse_temporal_constraints,
)
from continuum.query.failures import classify_result
from continuum.query.fixtures import build_cross_source_scenario


def _ctx(text: str, qid: str = "q1") -> QueryContext:
    return decompose_question({"question_id": qid, "question": text})


# ---- decomposition: intent -------------------------------------------------

def test_intent_ownership():
    assert classify_intent("Who currently owns Acme?") == "OWNERSHIP"


def test_intent_assignment():
    assert classify_intent("Who is assigned to the Acme onboarding?") == "ASSIGNMENT"


def test_intent_leadership():
    assert classify_intent("Who is the DRI for the payments service?") == "LEADERSHIP"


def test_intent_decision():
    assert classify_intent("Who decided to delay the Acme renewal?") == "DECISION"


def test_intent_history():
    assert classify_intent("Who used to own Acme before the handoff?") == "HISTORY"


def test_intent_conflict():
    assert classify_intent("Who actually owns Acme? The claims conflict.") == "CONFLICT"


def test_intent_provenance():
    assert classify_intent("Which source says Morgan owns Acme?") == "PROVENANCE"


def test_intent_provenance_claim_and_artifact():
    assert (
        classify_intent("Which claim and artifact support Soham Ratnaparkhi owning Acme?")
        == "PROVENANCE"
    )


def test_intent_source_presence():
    assert classify_intent("Does Slack or Gmail show the CedarBank handoff?") == "SOURCE_PRESENCE"


def test_intent_conflict_not_provenance_phrasing():
    assert classify_intent("Which claim contradicts the other on Acme?") == "CONFLICT"


def test_intent_dependency():
    assert classify_intent("Which project does payments depend on?") == "DEPENDENCY"


def test_intent_generic_fallback():
    assert classify_intent("What color is the sky?") == "GENERIC"


# ---- decomposition: entities ----------------------------------------------

def test_entities_quoted_pair():
    ctx = _ctx("Is 'Marcus Lin' the same as 'marcus.lin@redwood.com'?")
    roles = {e.mention: e.role for e in ctx.entities}
    assert roles.get("Marcus Lin") == "subject"
    assert "marcus.lin@redwood.com" in roles


def test_entities_name_pair():
    ctx = _ctx("Compare Priya with Morgan in the Acme ownership thread.")
    mentions = [e.mention for e in ctx.entities]
    assert "Priya" in mentions and "Morgan" in mentions


def test_entities_are_unresolved():
    ctx = _ctx("Who owns Acme?")
    for entity in ctx.entities:
        assert entity.canonical_key is None


# ---- decomposition: relationships -----------------------------------------

def test_relationship_hints():
    ctx = _ctx("Who owns Acme and maintains the acme-repo?")
    preds = {r.predicate for r in ctx.relationships}
    assert {"OWNS", "MAINTAINS"} <= preds


def test_relationship_only_graph_predicates():
    ctx = _ctx("Who decided to delay the Acme renewal?")
    preds = {r.predicate for r in ctx.relationships}
    assert preds <= {"OWNS", "MAINTAINS", "LEADS", "ASSIGNED_TO", "BLOCKS", "DEPENDS_ON", "REVIEWS"}


# ---- decomposition: temporal constraints ----------------------------------

def test_temporal_asof_explicit_date():
    ctx = _ctx("As of 2026-06-05, who owned Acme?")
    kinds = [c.kind for c in ctx.temporal]
    assert "as_of" in kinds
    assert any(c.value == "2026-06-05" for c in ctx.temporal)


def test_temporal_before_anchor():
    ctx = _ctx("Who owned Acme before the handoff?")
    kinds = [c.kind for c in ctx.temporal]
    assert "before" in kinds
    assert any("handoff" in (c.anchor or "") for c in ctx.temporal)


def test_temporal_after_anchor():
    ctx = _ctx("After the authentication outage, who decided to renew Acme?")
    kinds = [c.kind for c in ctx.temporal]
    assert "after" in kinds


def test_temporal_after_handoff_anchor():
    ctx = _ctx("Who owns Acme now after the handoff?")
    assert any(c.kind == "after" and (c.anchor or "").startswith("handoff") for c in ctx.temporal)
    assert any(c.kind == "current" for c in ctx.temporal)


def test_temporal_historical_tense():
    ctx = _ctx("Who used to own Acme?")
    assert any(c.kind == "historical" for c in ctx.temporal)


def test_temporal_current():
    ctx = _ctx("Who owns Acme now?")
    assert any(c.kind == "current" for c in ctx.temporal)


def test_temporal_none_for_plain_question():
    ctx = _ctx("Who owns Acme?")
    assert ctx.temporal == []


# ---- QueryContext serialization -------------------------------------------

def test_querycontext_roundtrip():
    ctx = _ctx("Who owned Acme before the handoff?", "q7")
    restored = QueryContext.from_dict(ctx.to_dict())
    assert restored == ctx


def test_querycontext_is_source_agnostic():
    ctx = _ctx("Which source says Morgan owns Acme?", "q8")
    assert ctx.question_id == "q8"
    assert set(ctx.to_dict()) == set(ctx.to_dict())


# ---- conflict ordering helpers (pure) -------------------------------------

def test_order_conflicts_by_observation_time():
    claims = [
        {"claim_id": "c1", "observed_at": "2026-06-10", "valid_from": "2026-06-10", "subject_id": "a"},
        {"claim_id": "c2", "observed_at": "2026-06-01", "valid_from": "2026-06-01", "subject_id": "b"},
    ]
    ordered = order_conflicts(claims)
    assert [c["claim_id"] for c in ordered] == ["c2", "c1"]


def test_intervals_disjoint_true_for_succession():
    ordered = [
        {"valid_from": "2026-05-01", "valid_to": "2026-06-09"},
        {"valid_from": "2026-06-10", "valid_to": "9999-12-31"},
    ]
    assert _intervals_disjoint(ordered) is True


def test_intervals_disjoint_false_for_overlap():
    ordered = [
        {"valid_from": "2026-06-01", "valid_to": "9999-12-31"},
        {"valid_from": "2026-06-10", "valid_to": "9999-12-31"},
    ]
    assert _intervals_disjoint(ordered) is False


# ---- failure taxonomy (pure) ----------------------------------------------

def test_classify_ok():
    result = {
        "state_result": {"status": "definitive", "value": {"name": "Morgan"}},
        "answer": "Morgan",
        "resolved_entities": ["account:acme"],
        "layers": {"retrieval": {"artifacts": 3}},
    }
    assert classify_result(result) == "OK"


def test_classify_conflict_miss():
    result = {
        "state_result": {"status": "conflict"},
        "answer": "",
        "resolved_entities": ["account:acme"],
        "layers": {},
    }
    assert classify_result(result) == "CONFLICT_MISS"


def test_classify_review_miss():
    result = {
        "state_result": {"status": "review"},
        "answer": "",
        "resolved_entities": ["account:acme"],
        "layers": {},
    }
    assert classify_result(result) == "CONFLICT_MISS"


def test_classify_retrieval_miss():
    result = {
        "state_result": {"status": "absent"},
        "answer": "unknown",
        "resolved_entities": [],
        "layers": {"retrieval": {"artifacts": 0}},
    }
    assert classify_result(result) == "RETRIEVAL_MISS"


def test_classify_insufficient_evidence():
    result = {
        "state_result": {"status": "absent"},
        "answer": "unknown",
        "resolved_entities": ["account:acme"],
        "layers": {"retrieval": {"artifacts": 2}},
    }
    assert classify_result(result) == "INSUFFICIENT_EVIDENCE"


def test_classify_abstention():
    result = {
        "state_result": {"status": "definitive"},
        "answer": "unknown - abstain",
        "resolved_entities": ["account:acme"],
        "layers": {},
    }
    assert classify_result(result) == "SAFE_ABSTENTION"


def test_classify_entity_resolution_miss():
    result = {
        "state_result": {"status": "absent"},
        "answer": "",
        "resolved_entities": [],
        "layers": {"entity_resolution": {"pair_verdict": "uncertain"}},
    }
    question = {"question": "Are 'Marcus Lin' and 'marcus.lin@redwood.com' the same person?"}
    assert classify_result(result, question=question) == "ENTITY_RESOLUTION_MISS"


def test_classify_error():
    result = {"error": "boom", "state_result": {}, "answer": "", "resolved_entities": [], "layers": {}}
    assert classify_result(result) == "INFRASTRUCTURE_ERROR"


# ---- fixtures -------------------------------------------------------------

def test_fixture_scenario_is_valid():
    scenario = build_cross_source_scenario()
    assert len(scenario["sources"]) == 5
    assert len(scenario["artifacts"]) == 6
    assert len(scenario["claims"]) == 5
    assert all(c.predicate in SUPPORTED_PREDICATES for c in scenario["claims"])
    assert all(c.observed_at for c in scenario["claims"])


def test_fixture_resolutions_cover_claims():
    scenario = build_cross_source_scenario()
    mentions = set()
    for claim in scenario["claims"]:
        mentions.add(claim.subject_mention)
        mentions.add(claim.object_mention)
    resolved = set()
    for definition in scenario["resolutions"].values():
        resolved.update(definition["mentions"])
    assert mentions <= resolved


def test_fixture_questions_decompose():
    scenario = build_cross_source_scenario()
    for q in scenario["questions"]:
        ctx = _ctx(q["question"], q["question_id"])
        assert ctx.question_id == q["question_id"]
    assert classify_intent(scenario["questions"][0]["question"]) == "OWNERSHIP"