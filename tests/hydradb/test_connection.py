import pytest

from continuum.hydradb import HydraDBClient


@pytest.mark.hydradb
def test_connection_and_trivial_query(client):
    assert client.health_check() is True
    result = client.execute(
        "MATCH (n:ContinuumHealthProbe {id: 1}) RETURN n.id AS id"
    )
    assert result.rows == []
    assert result.elapsed_ms >= 0
