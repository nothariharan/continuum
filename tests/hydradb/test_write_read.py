import pytest


@pytest.mark.hydradb
def test_create_read_and_parameterized_query(client):
    client.execute("MATCH (n) DETACH DELETE n")
    client.execute("CREATE (s:Person {id: 101, name: 'Sarah'})-[:OWNS]->(a:Account {id: 102, name: 'Acme'})")
    client.execute("CREATE (p:Project {id: 103, name: 'AcmeIntegration'})")
    client.execute("MATCH (p:Project {id: 103}), (a:Account {id: 102}) CREATE (p)-[:FOR]->(a)")
    names = client.execute("MATCH (n) RETURN n.name AS name ORDER BY name").rows
    assert [row["name"] for row in names] == ["Acme", "AcmeIntegration", "Sarah"]
    parameterized = client.execute("MATCH (n:Person {name: $name}) RETURN n.id AS id", {"name": "Sarah"})
    assert parameterized.rows == [{"id": 101}]


@pytest.mark.hydradb
def test_batch_write(client):
    result = client.execute_batch(
        "UNWIND $rows AS row MERGE (n:BatchProbe {id: row.id}) SET n.name = row.name",
        [{"id": 201, "name": "one"}, {"id": 202, "name": "two"}],
    )
    assert result.elapsed_ms >= 0
    rows = client.execute("MATCH (n:BatchProbe) RETURN n.name AS name ORDER BY name").rows
    assert [row["name"] for row in rows] == ["one", "two"]
