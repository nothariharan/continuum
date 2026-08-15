"""Known-good real-claim regression: 10 manually validated claims on real dsid
artifacts exercise current state, history, provenance, conflict, abstention,
non-OWNS predicates, and reset — against the same graph shape Phase 1 uses."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import count_claims, read_claim
from continuum.query import (
    resolve_conflicts,
    resolve_provenance,
    resolve_state,
    resolve_state_on,
)

ROOT = Path(__file__).resolve().parents[2]
REAL_CLAIMS = ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"
REAL_RESOLUTIONS = ROOT / "data" / "fixtures" / "phase2b" / "resolutions-real.json"


@pytest.fixture(scope="module")
def loaded_real_claims():
    try:
        with HydraDBClient() as client:
            client.health_check()
    except Exception as exc:
        pytest.skip(f"HydraDB must be running for real-claim regression tests: {exc}")
    subprocess.run(
        ["python", str(ROOT / "scripts" / "dataset_load_hydradb.py"), "--reset"],
        check=True,
    )
    subprocess.run(
        [
            "python",
            str(ROOT / "scripts" / "load_phase2b_claims.py"),
            "--reset",
            "--real",
            "--claims",
            str(REAL_CLAIMS),
            "--resolutions",
            str(REAL_RESOLUTIONS),
        ],
        check=True,
    )
    return True


@pytest.fixture
def client():
    with HydraDBClient() as value:
        yield value


@pytest.mark.hydradb
def test_real_claims_loaded(loaded_real_claims, client):
    assert count_claims(client) == 10


@pytest.mark.hydradb
def test_real_claim_read_back_with_evidence(loaded_real_claims, client):
    row = read_claim(client, "claim:may-patel-owns-lucentgrid")
    assert row is not None
    assert row["subject_mention"] == "Maya Patel"
    assert row["predicate"] == "OWNS"
    assert row["object_mention"] == "LucentGrid"
    assert row["subject_id"] == "person:may-patel"
    assert row["object_id"] == "account:lucentgrid"
    assert row["observed_at"] == "2027-02-11"
    assert "Owner: Maya Patel" in row["evidence_span"]


@pytest.mark.hydradb
def test_current_state_real_claims(loaded_real_claims, client):
    result = resolve_state(client, "account:lucentgrid", "OWNS")
    assert result["status"] == "definitive"
    assert result["value"] == {"entity_id": "person:may-patel", "name": "Maya Patel"}


@pytest.mark.hydradb
def test_historical_state_real_claims(loaded_real_claims, client):
    as_of = resolve_state_on(client, "account:lucentgrid", "2027-02-11", "OWNS")
    assert as_of["value"]["entity_id"] == "person:may-patel"
    before = resolve_state_on(client, "account:lucentgrid", "2026-01-01", "OWNS")
    assert before["status"] == "absent"
    assert before["value"] is None


@pytest.mark.hydradb
def test_provenance_traces_to_real_artifact(loaded_real_claims, client):
    result = resolve_provenance(client, "account:acme-health", "OWNS")
    assert result["status"] == "definitive"
    assert {item["claim_id"] for item in result["evidence"]} == {
        "claim:neha-owns-acme-health",
        "claim:priyom-owns-acme-health",
    }
    for item in result["evidence"]:
        assert item["artifact_id"] == "dsid_632713f6e1a745abb4a8ebb6da6f1dd8"
        assert item["artifact_kind"] == "gmail_message"
        assert item["source"] == "gmail"
    maintains = resolve_provenance(client, "account:acme-health", "MAINTAINS")
    assert maintains["evidence"][0]["artifact_id"] == "dsid_86d691cee0b548bcb22d8428dc7b6ce7"


@pytest.mark.hydradb
def test_conflict_real_claims_keeps_both_claims(loaded_real_claims, client):
    result = resolve_conflicts(client, "account:acme-health", "OWNS")
    assert result["status"] == "conflict"
    assert result["conflicting_subjects"] == ["person:neha-kapoor", "person:priyom-das"]
    assert len(result["claims"]) == 2
    contradicts = client.execute(
        "MATCH (a:Claim {key: 'claim:neha-owns-acme-health'})-[:CONTRADICTS]->(b:Claim) "
        "RETURN b.key AS key"
    ).rows
    assert contradicts == [{"key": "claim:priyom-owns-acme-health"}]
    assert count_claims(client) == 10


@pytest.mark.hydradb
def test_abstention_real_claims(loaded_real_claims, client):
    result = resolve_state(client, "account:cedarbank", "OWNS")
    assert result["status"] == "absent"
    assert result["value"] is None


@pytest.mark.hydradb
def test_non_owns_predicates_real_claims(loaded_real_claims, client):
    assert resolve_state(client, "account:skyline-systems", "MAINTAINS")["value"] == {
        "entity_id": "person:ravi-patel",
        "name": "Ravi Patel",
    }
    assert resolve_state(client, "account:skyline-systems", "LEADS")["value"] == {
        "entity_id": "person:may-chen",
        "name": "Maya Chen",
    }
    assert resolve_state(client, "account:acme-analytics", "MAINTAINS")["value"] == {
        "entity_id": "person:olga-petrov",
        "name": "Olga Petrov",
    }
    assert resolve_state(client, "account:lucentgrid", "ASSIGNED_TO")["value"] == {
        "entity_id": "person:ethan-cole",
        "name": "Ethan Cole",
    }


@pytest.mark.hydradb
def test_real_claims_reset_and_reload(loaded_real_claims, client):
    subprocess.run(
        [
            "python",
            str(ROOT / "scripts" / "load_phase2b_claims.py"),
            "--reset",
            "--real",
            "--claims",
            str(REAL_CLAIMS),
            "--resolutions",
            str(REAL_RESOLUTIONS),
        ],
        check=True,
    )
    assert count_claims(client) == 10
    assert resolve_state(client, "account:lucentgrid", "OWNS")["value"]["entity_id"] == "person:may-patel"
