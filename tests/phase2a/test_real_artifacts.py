"""Phase 2A real-dataset integration: load normalized Artifacts, read back, latency."""

from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path

import pytest

from continuum.hydradb import HydraDBClient
from continuum.hydradb.artifacts import (
    ID_OFFSET,
    count_artifacts,
    delete_all_artifacts,
    load_artifacts,
    read_artifact,
)

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "samples" / "phase2a-sample.jsonl"


@pytest.fixture(scope="module")
def loaded_artifacts(client):
    delete_all_artifacts(client)
    records = []
    with SAMPLE.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    result = load_artifacts(client, records)
    yield {"records": records, "result": result}


@pytest.mark.hydradb
def test_real_artifacts_load(loaded_artifacts, client):
    records = loaded_artifacts["records"]
    assert count_artifacts(client) == len(records)


@pytest.mark.hydradb
def test_real_artifacts_read_back(loaded_artifacts, client):
    records = loaded_artifacts["records"]
    mismatches = 0
    missing = 0
    for index, record in enumerate(records, start=1):
        row = read_artifact(client, ID_OFFSET + index)
        if row is None:
            missing += 1
        elif row["title"] != record["title"] or row["source"] != record["source"]:
            mismatches += 1
    assert missing == 0
    assert mismatches == 0


@pytest.mark.hydradb
def test_real_artifacts_lookup_latency(loaded_artifacts, client):
    records = loaded_artifacts["records"]
    import time

    latencies = []
    for index in range(1, 51):
        t0 = time.perf_counter()
        row = read_artifact(client, ID_OFFSET + index)
        latencies.append((time.perf_counter() - t0) * 1000)
        assert row is not None
    assert statistics.median(latencies) < 50


@pytest.mark.hydradb
def test_real_artifacts_survive_phase1_reseed():
    subprocess.run(["python", str(ROOT / "scripts" / "seed_synthetic_company.py"), "--reset"], check=True)
    with HydraDBClient() as client:
        rows = client.execute("MATCH (n:Claim) RETURN count(*) AS n").rows
        assert rows[0]["n"] > 0