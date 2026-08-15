"""Phase 2B query latency baseline on the known-good real-claim fixture.

Default: the synthetic real-shaped fixture (docs/phase-2b-benchmark.json).
--real: the manually validated real-dsid fixture (docs/phase-2b-real-benchmark.json),
which also records claim ingestion latency (loader write + read-back verify).

Phase 1 baseline lives in docs/phase-1-benchmark.json and is reported
alongside so the real-claim path is measured against it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from continuum.hydradb import HydraDBClient
from continuum.query import (
    resolve_conflicts,
    resolve_provenance,
    resolve_state,
    resolve_state_on,
)

ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * p
    lower, upper = int(index), min(int(index) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def load_fixture(real: bool) -> float:
    """Seed the fixture and return the loader's write+verify latency (ms)."""
    if real:
        subprocess.run(
            ["python", str(ROOT / "scripts" / "dataset_load_hydradb.py"), "--reset"],
            check=True,
        )
        cmd = [
            "python",
            str(ROOT / "scripts" / "load_phase2b_claims.py"),
            "--reset",
            "--real",
            "--claims",
            str(ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"),
            "--resolutions",
            str(ROOT / "data" / "fixtures" / "phase2b" / "resolutions-real.json"),
        ]
    else:
        cmd = ["python", str(ROOT / "scripts" / "load_phase2b_claims.py"), "--reset"]
    started = time.perf_counter()
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return (time.perf_counter() - started) * 1000


def main(iterations: int = 20, real: bool = False) -> dict:
    ingestion_ms = load_fixture(real)
    if real:
        operations = {
            "current_state": lambda c: resolve_state(c, "account:lucentgrid", "OWNS"),
            "historical_state": lambda c: resolve_state_on(c, "account:lucentgrid", "2026-01-01", "OWNS"),
            "provenance": lambda c: resolve_provenance(c, "account:acme-health", "OWNS"),
            "conflict": lambda c: resolve_conflicts(c, "account:acme-health", "OWNS"),
            "maintains_state": lambda c: resolve_state(c, "account:skyline-systems", "MAINTAINS"),
            "leads_state": lambda c: resolve_state(c, "account:skyline-systems", "LEADS"),
            "assigned_state": lambda c: resolve_state(c, "account:lucentgrid", "ASSIGNED_TO"),
            "abstention": lambda c: resolve_state(c, "account:cedarbank", "OWNS"),
        }
    else:
        operations = {
            "current_state": lambda c: resolve_state(c, "account:cedarbank", "OWNS"),
            "historical_state": lambda c: resolve_state_on(c, "account:cedarbank", "2026-06-01", "OWNS"),
            "provenance": lambda c: resolve_provenance(c, "account:cedarbank", "OWNS"),
            "conflict": lambda c: resolve_conflicts(c, "account:cedarbank", "OWNS"),
            "maintains_state": lambda c: resolve_state(c, "project:optimize-conductor", "MAINTAINS"),
            "depends_state": lambda c: resolve_state(c, "project:hosted-api", "DEPENDS_ON"),
            "abstention": lambda c: resolve_state(c, "account:orionai", "OWNS"),
        }
    measurements = {}
    with HydraDBClient() as client:
        for name, operation in operations.items():
            samples = []
            for _ in range(iterations):
                started = time.perf_counter()
                result = operation(client)
                samples.append((time.perf_counter() - started) * 1000)
                if not result:
                    raise RuntimeError(f"benchmark operation returned no result: {name}")
            measurements[name] = {
                "p50_ms": round(percentile(samples, 0.50), 3),
                "p95_ms": round(percentile(samples, 0.95), 3),
                "p99_ms": round(percentile(samples, 0.99), 3),
                "iterations": iterations,
            }
    return {
        "ingestion": {"load_verify_ms": round(ingestion_ms, 2)},
        "queries": measurements,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true", help="benchmark the real-dsid known-good fixture")
    args = parser.parse_args()
    result = main(real=args.real)
    phase1 = {}
    phase1_path = ROOT / "docs" / "phase-1-benchmark.json"
    if phase1_path.exists():
        phase1 = json.loads(phase1_path.read_text(encoding="utf-8"))
    print(json.dumps({"phase2b": result, "phase1_reference": phase1}, indent=2))
    output = ROOT / ("docs/phase-2b-real-benchmark.json" if args.real else "docs/phase-2b-benchmark.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
