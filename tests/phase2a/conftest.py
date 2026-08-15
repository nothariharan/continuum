import pytest

from continuum.hydradb import HydraDBClient


@pytest.fixture(scope="module")
def client():
    with HydraDBClient() as value:
        yield value