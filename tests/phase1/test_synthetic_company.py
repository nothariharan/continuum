import pytest

from continuum.query import current_owner, find_conflicts, owner_on, ownership_provenance


@pytest.mark.hydradb
def test_seed_synthetic_company(client):
    assert client.execute("MATCH (n:Person) RETURN n.key AS key ORDER BY key").rows == [
        {"key": "person:arjun"}, {"key": "person:sarah"}, {"key": "person:soham"}
    ]
    assert client.execute("MATCH (n:Claim) RETURN n.key AS key").rows
    assert client.execute("MATCH (n:Person {key: 'person:soham'}) RETURN n.aliases AS aliases").rows == [
        {"aliases": "Sam|@soham|S. Ratnaparkhi|soham-dev"}
    ]


@pytest.mark.hydradb
def test_current_owner(client):
    result = current_owner(client, "account:acme")
    assert result["status"] == "definitive"
    assert result["value"] == {"entity_id": "person:sarah", "name": "Sarah Chen"}


@pytest.mark.hydradb
def test_historical_owner(client):
    result = owner_on(client, "account:acme", "2026-07-15")
    assert result["value"] == {"entity_id": "person:arjun", "name": "Arjun Mehta"}
    assert owner_on(client, "account:acme", "2026-08-13")["value"]["entity_id"] == "person:sarah"


@pytest.mark.hydradb
def test_provenance(client):
    result = ownership_provenance(client, "account:acme")
    assert result["value"]["name"] == "Sarah Chen"
    assert {item["source"] for item in result["evidence"]} == {"Gmail", "Linear", "Slack"}
    assert {item["claim_id"] for item in result["evidence"]} == {
        "claim:arjun-acme-gmail", "claim:sarah-acme-linear", "claim:sarah-acme-slack"
    }


@pytest.mark.hydradb
def test_conflict_detection(client):
    result = find_conflicts(client, "account:acme")
    assert result["status"] == "conflict"
    assert result["conflicting_subjects"] == ["person:arjun", "person:sarah"]
    assert len(result["claims"]) == 3
    assert client.execute(
        "MATCH (a:Claim {key: 'claim:arjun-acme-gmail'})-[:CONTRADICTS]->(b:Claim) RETURN b.key AS key ORDER BY key"
    ).rows == [{"key": "claim:sarah-acme-linear"}, {"key": "claim:sarah-acme-slack"}]


@pytest.mark.hydradb
def test_absent_query(client):
    result = current_owner(client, "account:stripeco")
    assert result["status"] == "absent"
    assert result["value"] is None
