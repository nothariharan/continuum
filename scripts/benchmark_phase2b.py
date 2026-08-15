"""Phase 2B real-claim query latency baseline, compared with Phase 1 numbers.

Writes docs/phase-2b-benchmark.json. Phase 1 baseline lives in
docs/phase-1-benchmark.json (p50 ~2.4 ms, p95 ~4.2 ms, p99 ~7.7 ms) and is
reported alongside so the real-claim path is measured against it.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from continuum.hydradb import HydraDBClient
from continuum.query import (
    resolve_conflicts,
    resolve_provenance,
    resolve_state,
    resolve_state_on,
)


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * p
    lower, upper = int(index), min(int(index) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def main(iterations: int = 20) -> dict:
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
    return measurements


if __name__ == "__main__":
    result = main()
    phase1 = {}
    phase1_path = Path("docs/phase-1-benchmark.json")
    if phase1_path.exists():
        phase1 = json.loads(phase1_path.read_text(encoding="utf-8"))
    print(json.dumps({"phase2b": result, "phase1_reference": phase1}, indent=2))
    output = Path("docs/phase-2b-benchmark.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
