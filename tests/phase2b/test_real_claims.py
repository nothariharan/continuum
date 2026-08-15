"""Phase 2B integration: real-shaped claims load, read back, state, conflict,
provenance, abstention — against the same graph shape Phase 1 uses."""

from __future__ import annotations

import pytest

from continuum.hydradb.claims import count_claims, read_claim
from continuum.query import (
    resolve_conflicts,
    resolve_provenance,
    resolve_state,
    resolve_state_on,
)


@pytest.mark.hydradb
def test_claims_loaded(loaded_real_claims, client):
    assert count_claims(client) == 9


@pytest.mark.hydradb
def test_claim_read_back(loaded_real_claims, client):
    row = read_claim(client, "claim:camila-owns-cedarbank")
    assert row is not None
    assert row["subject_mention"] == "Camila Reyes"
    assert row["predicate"] == "OWNS"
    assert row["object_mention"] == "CedarBank"
    assert row["subject_id"] == "person:camila-reyes"
    assert row["object_id"] == "account:cedarbank"
    assert row["observed_at"] == "2026-06-25"
    assert row["valid_from"] == "2026-06-20"
    assert row["valid_to"] == "9999-12-31"
    assert row["confidence"] == 0.94
    assert row["extraction_method"] == "hand-written"
    assert row["evidence_span"]


@pytest.mark.hydradb
def test_claim_traces_to_artifact(loaded_real_claims, client):
    rows = client.execute(
        "MATCH (c:Claim {key: 'claim:camila-owns-cedarbank'})-[:SOURCED_FROM]->(a:Artifact)-[:FROM]->(s:Source) "
        "RETURN a.key AS artifact_id, a.kind AS kind, s.key AS source_id, s.name AS source_name"
    ).rows
    assert rows == [
        {
            "artifact_id": "artifact:linear-cedarbank-owner",
            "kind": "linear_ticket",
            "source_id": "source:linear",
            "source_name": "Linear",
        }
    ]


@pytest.mark.hydradb
def test_current_state_real_claims(loaded_real_claims, client):
    result = resolve_state(client, "account:cedarbank", "OWNS")
    assert result["status"] == "definitive"
    assert result["value"] == {"entity_id": "person:camila-reyes", "name": "Camila Reyes"}
    assert result["valid_from"] == "2026-06-20"


@pytest.mark.hydradb
def test_historical_state_real_claims(loaded_real_claims, client):
    result = resolve_state_on(client, "account:cedarbank", "2026-06-01", "OWNS")
    assert result["value"] == {"entity_id": "person:may-patel", "name": "Maya Patel"}
    assert resolve_state_on(client, "account:cedarbank", "2026-06-25", "OWNS")["value"]["entity_id"] == "person:camila-reyes"


@pytest.mark.hydradb
def test_predicate_states(loaded_real_claims, client):
    assert resolve_state(client, "project:optimize-conductor", "OWNS")["value"] == {
        "entity_id": "person:ava-nguyen",
        "name": "Ava Nguyen",
    }
    assert resolve_state(client, "project:optimize-conductor", "MAINTAINS")["value"] == {
        "entity_id": "person:diego-martinez",
        "name": "Diego Martinez",
    }
    assert resolve_state(client, "project:optimize-conductor", "REVIEWS")["value"] == {
        "entity_id": "person:liam-oconnor",
        "name": "Liam O'Connor",
    }
    assert resolve_state(client, "project:hosted-api", "DEPENDS_ON")["value"] == {
        "entity_id": "project:optimize-conductor",
        "name": "Optimize Conductor",
    }


@pytest.mark.hydradb
def test_provenance_real_claims(loaded_real_claims, client):
    result = resolve_provenance(client, "account:cedarbank", "OWNS")
    assert result["value"]["name"] == "Camila Reyes"
    assert {item["source"] for item in result["evidence"]} == {"Gmail", "Slack", "Linear"}
    assert {item["claim_id"] for item in result["evidence"]} == {
        "claim:may-owns-cedarbank",
        "claim:camila-takes-cedarbank",
        "claim:camila-owns-cedarbank",
    }


@pytest.mark.hydradb
def test_conflict_detection_real_claims(loaded_real_claims, client):
    result = resolve_conflicts(client, "account:cedarbank", "OWNS")
    assert result["status"] == "CONFLICT"
    assert result["conflicting_subjects"] == ["person:camila-reyes", "person:may-patel"]
    assert len(result["claims"]) == 3
    contradicts = client.execute(
        "MATCH (a:Claim {key: 'claim:may-owns-cedarbank'})-[:CONTRADICTS]->(b:Claim) RETURN b.key AS key ORDER BY key"
    ).rows
    assert contradicts == [{"key": "claim:camila-owns-cedarbank"}, {"key": "claim:camila-takes-cedarbank"}]


@pytest.mark.hydradb
def test_consistent_predicate_not_conflicted(loaded_real_claims, client):
    result = resolve_conflicts(client, "project:optimize-conductor", "OWNS")
    assert result["status"] == "CONSISTENT"
    assert result["conflicting_subjects"] == ["person:ava-nguyen"]


@pytest.mark.hydradb
def test_abstention_real_claims(loaded_real_claims, client):
    result = resolve_state(client, "account:orionai", "OWNS")
    assert result["status"] == "ABSENT"
    assert result["value"] is None


@pytest.mark.hydradb
def test_mentions_preserved_alongside_resolution(loaded_real_claims, client):
    rows = client.execute(
        "MATCH (c:Claim)-[:ABOUT]->(a:Account {key: 'account:cedarbank'}) "
        "RETURN c.subject_mention AS mention ORDER BY mention"
    ).rows
    assert {row["mention"] for row in rows} == {"Camila Reyes", "Maya Patel"}
