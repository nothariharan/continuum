"""Semantic state interface tests — the future MCP/API contract (Y10).

Verifies the adapter delegates to the stable resolvers and returns the
canonical envelope, without wiring MCP. The known-good fixture loads real
claims so state/history/conflict/provenance have data to answer.
"""

from __future__ import annotations

import pytest

from continuum.query.semantic import StateQueryAdapter


@pytest.mark.hydradb
def test_all_operations_use_canonical_envelope(loaded_real_claims, client):
    adapter = StateQueryAdapter(client)
    operations = [
        adapter.get_current_state("account:cedarbank"),
        adapter.get_state_as_of("account:cedarbank", "2026-06-01"),
        adapter.get_history("account:cedarbank"),
        adapter.get_conflicts("account:cedarbank"),
        adapter.get_evidence("account:cedarbank"),
        adapter.get_dependencies("account:cedarbank"),
    ]
    for payload in operations:
        assert isinstance(payload, dict)
        assert payload["status"] in {"definitive", "absent", "consistent", "conflict"}


@pytest.mark.hydradb
def test_conflict_and_provenance_answers(loaded_real_claims, client):
    adapter = StateQueryAdapter(client)
    conflicts = adapter.get_conflicts("account:cedarbank")
    assert conflicts["status"] == "conflict"
    assert set(conflicts["conflicting_subjects"]) == {"person:camila-reyes", "person:may-patel"}

    evidence = adapter.get_evidence("account:cedarbank")
    assert evidence["status"] == "definitive"
    assert any(item["source"] in {"Gmail", "Slack", "Linear"} for item in evidence["evidence"])


@pytest.mark.hydradb
def test_abstention_is_explicit(loaded_real_claims, client):
    adapter = StateQueryAdapter(client)
    state = adapter.get_current_state("account:orionai")
    assert state["status"] == "absent"
    assert state["value"] is None


@pytest.mark.hydradb
def test_history_ordering(loaded_real_claims, client):
    adapter = StateQueryAdapter(client)
    history = adapter.get_history("account:cedarbank")
    assert history["status"] == "definitive"
    dates = [item["valid_from"] for item in history["history"]]
    assert dates == sorted(dates)


def test_resolve_entity_passthrough():
    from continuum.hydradb import HydraDBClient

    with HydraDBClient() as client:
        adapter = StateQueryAdapter(client)
        payload = adapter.resolve_entity("person:may-patel")
        assert payload["entity_key"] == "person:may-patel"
        assert payload["resolver"] == "passthrough"
