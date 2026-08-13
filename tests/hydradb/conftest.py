import pytest

from continuum.hydradb import HydraDBClient


@pytest.fixture
def client():
    with HydraDBClient() as value:
        yield value


@pytest.fixture(autouse=True)
def hydradb_required(request):
    if request.node.get_closest_marker("hydradb") is None:
        return
    if request.node.name == "test_reset_recreates_empty_development_state":
        return
    try:
        with HydraDBClient() as value:
            value.health_check()
    except Exception as exc:
        pytest.skip(f"HydraDB integration test requires a ready local instance: {exc}")
