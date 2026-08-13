import subprocess
from pathlib import Path

import pytest


@pytest.mark.hydradb
def test_reset_recreates_empty_development_state():
    root = Path(__file__).resolve().parents[2]
    scripts = root / "scripts"
    docker_check = subprocess.run(["docker", "info"], capture_output=True)
    if docker_check.returncode != 0:
        pytest.skip("Docker Desktop Linux engine is not running")
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(scripts / "reset_hydradb.ps1")],
        check=True,
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(scripts / "start_hydradb.ps1")],
        check=True,
    )
    from continuum.hydradb import HydraDBClient

    with HydraDBClient() as client:
        assert client.execute(
            "MATCH (n:ContinuumHealthProbe {id: 1}) RETURN n.id AS id"
        ).rows == []
