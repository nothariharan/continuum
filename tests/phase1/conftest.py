from pathlib import Path
import subprocess

import pytest

from continuum.hydradb import HydraDBClient


@pytest.fixture(scope="session", autouse=True)
def seeded_company():
    root = Path(__file__).resolve().parents[2]
    try:
        with HydraDBClient() as client:
            client.health_check()
    except Exception as exc:
        pytest.skip(f"HydraDB must be running for Phase 1 integration tests: {exc}")
    subprocess.run(["python", str(root / "scripts" / "seed_synthetic_company.py"), "--reset"], check=True)
    yield


@pytest.fixture
def client():
    with HydraDBClient() as value:
        yield value

