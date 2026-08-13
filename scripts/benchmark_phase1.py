"""Small repeatable Phase 1 query latency baseline."""

from __future__ import annotations

import json
import time
from pathlib import Path

from continuum.hydradb import HydraDBClient
from continuum.query import current_owner, find_conflicts, owner_on, ownership_provenance


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * p
    lower, upper = int(index), min(int(index) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def main(iterations: int = 20) -> dict:
    operations = {
        "current_state": lambda c: current_owner(c, "account:acme"),
        "historical_state": lambda c: owner_on(c, "account:acme", "2026-07-15"),
        "provenance": lambda c: ownership_provenance(c, "account:acme"),
        "conflict": lambda c: find_conflicts(c, "account:acme"),
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
    print(json.dumps(result, indent=2))
    output = Path("docs/phase-1-benchmark.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
