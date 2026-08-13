import pytest


@pytest.mark.hydradb
def test_relationship_and_bounded_traversal(client):
    direct = client.execute("MATCH (s:Person {name: 'Sarah'})-[:OWNS]->(a:Account) RETURN a.name AS name")
    assert direct.rows == [{"name": "Acme"}]
    bounded = client.execute(
        "MATCH (s:Person {name: 'Sarah'})-[:OWNS*1..2]->(n) RETURN n.name AS name ORDER BY name"
    )
    assert bounded.rows == [{"name": "Acme"}]

