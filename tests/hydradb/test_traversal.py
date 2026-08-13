import pytest


@pytest.mark.hydradb
def test_relationship_and_bounded_traversal(client):
    client.execute("CREATE (s:Person {id: 301, name: 'Sarah'})-[:OWNS]->(a:Account {id: 302, name: 'Acme'})")
    direct = client.execute("MATCH (s:Person {name: 'Sarah'})-[:OWNS]->(a:Account) RETURN a.name AS name")
    assert direct.rows == [{"name": "Acme"}]
    bounded = client.execute(
        "MATCH (s {id: 301})-[:OWNS*1..2]->(n) RETURN n.name AS name ORDER BY name"
    )
    assert bounded.rows == [{"name": "Acme"}]
    client.execute("MATCH (s:Person {id: 301}) DETACH DELETE s")
    client.execute("MATCH (a:Account {id: 302}) DETACH DELETE a")
