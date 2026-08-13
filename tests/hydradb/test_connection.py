import pytest

from continuum.hydradb import HydraDBClient


@pytest.mark.hydradb
def test_connection_and_trivial_query(client):
    assert client.health_check() is True
    result = client.execute("RETURN 1 AS ok")
    assert result.rows == [{"ok": 1}]
    assert result.elapsed_ms >= 0

