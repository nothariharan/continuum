import pytest

from continuum.hydradb.health import diagnose


@pytest.mark.hydradb
def test_health_is_reachable_ready_authenticated_and_queryable():
    status = diagnose()
    assert status.reachable and status.ready and status.authenticated and status.queryable

