import json
import subprocess
from pathlib import Path

import pytest

from continuum.hydradb import HydraDBClient

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session", autouse=True)
def loaded_real_claims():
    try:
        with HydraDBClient() as client:
            client.health_check()
    except Exception as exc:
        pytest.skip(f"HydraDB must be running for Phase 2B integration tests: {exc}")
    subprocess.run(
        ["python", str(ROOT / "scripts" / "load_phase2b_claims.py"), "--reset"],
        check=True,
    )
    yield


@pytest.fixture
def client():
    with HydraDBClient() as value:
        yield value
