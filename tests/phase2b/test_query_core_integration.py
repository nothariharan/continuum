"""Core-query integration test — cross-source fixtures through the full
graph path. Requires a running local HydraDB (hydradb marker).

Path exercised:

    fixtures (Slack/Gmail/GitHub/Jira/Fireflies)
      -> hydradb.claims.load_claims
      -> decompose_question (QueryContext)
      -> continuum.benchmark.answer (retrieval -> entity -> state -> evidence)
      -> answer + provenance + failure classification
"""

from __future__ import annotations

import pytest

from continuum.benchmark import answer
from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import load_claims
from continuum.query.conflict import resolve_conflict_state
from continuum.query.failures import classify_result
from continuum.query.fixtures import build_cross_source_scenario
from continuum.query.state import resolve_state, resolve_state_on
from continuum.query.temporal import resolve_state_before


@pytest.mark.hydradb
def test_fixture_load_and_ownership_succession(client: HydraDBClient):
    scenario = build_cross_source_scenario()
    load_result = load_claims(
        client,
        claims=scenario["claims"],
        resolutions=scenario["resolutions"],
        fixture_artifacts=scenario["artifacts"],
        fixture_sources=scenario["sources"],
        reset=True,
    )
    assert load_result.claims_written == len(scenario["claims"])

    # Succession is not current: two overlapping claims make it a conflict.
    conflict = resolve_conflict_state(client, "account:acme", "OWNS")
    assert conflict["status"] == "conflict"
    assert set(conflict["conflicting_subjects"]) == {"person:priya", "person:morgan"}


@pytest.mark.hydradb
def test_asof_ownership_resolves_to_priya(client: HydraDBClient):
    scenario = build_cross_source_scenario()
    load_claims(
        client,
        claims=scenario["claims"],
        resolutions=scenario["resolutions"],
        fixture_artifacts=scenario["artifacts"],
        fixture_sources=scenario["sources"],
        reset=True,
    )
    state = resolve_state_on(client, "account:acme", "2026-06-05", "OWNS")
    assert state["status"] == "definitive"
    assert state["value"]["entity_id"] == "person:priya"


@pytest.mark.hydradb
def test_before_handoff_ownership_is_priya(client: HydraDBClient):
    scenario = build_cross_source_scenario()
    load_claims(
        client,
        claims=scenario["claims"],
        resolutions=scenario["resolutions"],
        fixture_artifacts=scenario["artifacts"],
        fixture_sources=scenario["sources"],
        reset=True,
    )
    state = resolve_state_before(client, "account:acme", "2026-06-10", "OWNS")
    assert state["status"] == "definitive"
    assert state["value"]["entity_id"] == "person:priya"
    assert state["resolution"] == "before"


@pytest.mark.hydradb
def test_maintains_resolves_to_morgan(client: HydraDBClient):
    scenario = build_cross_source_scenario()
    load_claims(
        client,
        claims=scenario["claims"],
        resolutions=scenario["resolutions"],
        fixture_artifacts=scenario["artifacts"],
        fixture_sources=scenario["sources"],
        reset=True,
    )
    state = resolve_state(client, "project:acme-repo", "MAINTAINS")
    assert state["status"] == "definitive"
    assert state["value"]["entity_id"] == "person:morgan"


@pytest.mark.hydradb
def test_pipeline_answers_with_query_context_and_provenance(client: HydraDBClient):
    scenario = build_cross_source_scenario()
    load_claims(
        client,
        claims=scenario["claims"],
        resolutions=scenario["resolutions"],
        fixture_artifacts=scenario["artifacts"],
        fixture_sources=scenario["sources"],
        reset=True,
    )

    result = answer(
        client,
        {
            "question_id": "q_cross_asof",
            "question": "As of 2026-06-05, who owned Acme?",
            "predicate": "OWNS",
            "evidence_entity": "account:acme",
        },
    )
    assert result["query_context"]["intent"] == "OWNERSHIP"
    assert result["state_result"]["status"] == "definitive"
    assert result["state_result"]["value"]["name"] == "Priya"
    assert classify_result(result) == "OK"

    evidence = result["evidence"]
    assert evidence, "answer must carry provenance"
    assert any(item["artifact_id"] for item in evidence)
    assert any(item["source"] for item in evidence)


@pytest.mark.hydradb
def test_pipeline_conflict_classification(client: HydraDBClient):
    scenario = build_cross_source_scenario()
    load_claims(
        client,
        claims=scenario["claims"],
        resolutions=scenario["resolutions"],
        fixture_artifacts=scenario["artifacts"],
        fixture_sources=scenario["sources"],
        reset=True,
    )
    result = answer(
        client,
        {
            "question_id": "q_cross_current",
            "question": "Who actually owns Acme right now?",
            "predicate": "OWNS",
            "evidence_entity": "account:acme",
        },
    )
    assert result["state_result"]["status"] in {"conflict", "review"}
    assert classify_result(result) == "CONFLICT_MISS"


@pytest.mark.hydradb
def test_pipeline_before_handoff_answer(client: HydraDBClient):
    scenario = build_cross_source_scenario()
    load_claims(
        client,
        claims=scenario["claims"],
        resolutions=scenario["resolutions"],
        fixture_artifacts=scenario["artifacts"],
        fixture_sources=scenario["sources"],
        reset=True,
    )
    result = answer(
        client,
        {
            "question_id": "q_cross_before",
            "question": "Who owned Acme before the handoff?",
            "predicate": "OWNS",
            "evidence_entity": "account:acme",
        },
    )
    assert result["state_result"]["status"] == "definitive"
    assert result["state_result"]["value"]["name"] == "Priya"
    assert result["state_result"]["resolution"] == "before"