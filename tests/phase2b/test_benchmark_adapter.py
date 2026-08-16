"""Continuum benchmark adapter tests — contract, pipeline, layers."""

from __future__ import annotations

import json

import pytest

from continuum.benchmark import answer
from continuum.benchmark.contract import LAYER_NAMES, empty_result, validate_result
from continuum.benchmark.pipeline import _default_answer_generator, _extract_mentions
from continuum.entities.store import EntityStore

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def test_empty_result_has_all_contract_fields():
    result = empty_result("q1", "Who owns Acme?")
    validate_result(result)
    for name in LAYER_NAMES:
        assert name in result["layers"]


def test_validate_result_rejects_missing_fields():
    result = empty_result("q1", "x")
    del result["answer"]
    try:
        validate_result(result)
        assert False, "missing field must raise"
    except ValueError:
        pass


def test_extract_mentions_quoted():
    mentions = _extract_mentions("Is 'Marcus Lin' the same as 'marcus.lin@redwood.com'?")
    assert mentions[0] == "Marcus Lin"
    assert "marcus.lin@redwood.com" in mentions[1]


def test_extract_mentions_emails():
    mentions = _extract_mentions("Compare a@b.com with c@d.com")
    assert len(mentions) >= 1


def test_default_answer_generator_absent():
    result = empty_result("q1", "x")
    result["state_result"] = {"status": "absent"}
    assert _default_answer_generator(result) == "unknown"


def test_default_answer_generator_conflict():
    result = empty_result("q1", "x")
    result["state_result"] = {"status": "conflict", "conflicting_subjects": ["a", "b"]}
    assert _default_answer_generator(result) == "conflict: a or b"


def test_default_answer_generator_value():
    result = empty_result("q1", "x")
    result["state_result"] = {"status": "definitive", "value": {"name": "Maya Patel"}}
    assert _default_answer_generator(result) == "Maya Patel"


@pytest.fixture(scope="module")
def real_fixture_graph():
    """Load the real-claims fixture once per module (isolated from other
    tests via dataset_load_hydradb --reset + claims --reset)."""
    import subprocess
    import sys

    try:
        from continuum.hydradb import HydraDBClient

        with HydraDBClient() as client:
            client.health_check()
    except Exception as exc:
        pytest.skip(f"HydraDB must be running: {exc}")

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "dataset_load_hydradb.py"), "--reset"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "load_phase2b_claims.py"), "--reset", "--real",
         "--claims", str(ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"),
         "--resolutions", str(ROOT / "data" / "fixtures" / "phase2b" / "resolutions-real.json")],
        check=True, capture_output=True, text=True,
    )
    return True


@pytest.mark.hydradb
def test_answer_contract_on_real_fixture(real_fixture_graph, client):
    store = EntityStore(client)
    question = {
        "question_id": "q-single-01",
        "category": "single-hop",
        "question": "Who owns LucentGrid?",
        "evidence_entity": "account:lucentgrid",
        "predicate": "OWNS",
    }
    result = answer(client, question, entity_store=store)
    validate_result(result)
    assert result["answer"] == "Maya Patel"
    assert result["status"] == "definitive"
    assert result["context"]["claims"] >= 1
    assert result["latency_ms"]["total"] > 0


@pytest.mark.hydradb
def test_answer_conflict_detected(real_fixture_graph, client):
    question = {
        "question_id": "q-conflict-01",
        "category": "conflict",
        "question": "Who owns Acme Health?",
        "evidence_entity": "account:acme-health",
        "predicate": "OWNS",
    }
    result = answer(client, question, entity_store=EntityStore(client))
    assert result["status"] == "conflict"
    assert set(result["conflicts"]) == {"person:neha-kapoor", "person:priyom-das"}


@pytest.mark.hydradb
def test_answer_temporal_abstention(real_fixture_graph, client):
    question = {
        "question_id": "q-temporal-02",
        "category": "temporal",
        "question": "Who owned LucentGrid before any evidence (2026-01-01)?",
        "evidence_entity": "account:lucentgrid",
        "predicate": "OWNS",
    }
    result = answer(client, question, entity_store=EntityStore(client))
    assert result["status"] == "absent"
    assert result["answer"] == "unknown"


def test_hard_questions_fixture_shape():
    rows = [json.loads(line) for line in (ROOT / "benchmark" / "regression" / "questions.jsonl").open(encoding="utf-8") if line.strip()]
    assert len(rows) == 18
    categories = {r["category"] for r in rows}
    assert {"single-hop", "multi-hop", "temporal", "conflict", "abstention", "provenance", "entity-resolution"} <= categories
