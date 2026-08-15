"""Load the normalized Phase 2A sample into HydraDB and verify read-back.

Phase 2A only: stores :Artifact nodes. No claims graph or entity resolution.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from time import perf_counter

from continuum.hydradb import HydraDBClient
from continuum.hydradb.artifacts import (
    ID_OFFSET,
    count_artifacts,
    delete_all_artifacts,
    load_artifacts,
    read_artifact,
)

DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples"


def main() -> int:
    parser = argparse.ArgumentParser(description="Load the Phase 2A sample into HydraDB")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--cap", type=int, default=360, help="max artifacts to load")
    parser.add_argument("--reset", action="store_true", help="delete existing Artifact nodes first")
    args = parser.parse_args()

    records = []
    with (args.sample / "phase2a-sample.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    records = records[: args.cap]

    with HydraDBClient() as client:
        if args.reset:
            delete_all_artifacts(client)
        result = load_artifacts(client, records)
        count = count_artifacts(client)

        mismatch = 0
        for index, record in enumerate(records, start=1):
            row = read_artifact(client, ID_OFFSET + index)
            if row is None:
                mismatch += 1
                continue
            if row["title"] != record["title"] or row["source"] != record["source"]:
                mismatch += 1

        lookup_ms = []
        for index in range(1, 26):
            t0 = perf_counter()
            read_artifact(client, ID_OFFSET + index)
            lookup_ms.append((perf_counter() - t0) * 1000)

        payload = {
            "loaded": result.written,
            "read_back_count": result.read_back_count,
            "count_in_db": count,
            "mismatches": mismatch,
            "load_ms_total": round(result.load_ms, 2),
            "read_back_ms": round(result.read_back_ms, 2),
            "lookup_latency_ms": {
                "n": len(lookup_ms),
                "p50": round(statistics.median(lookup_ms), 3),
                "p95": round(sorted(lookup_ms)[int(0.95 * len(lookup_ms)) - 1], 3) if lookup_ms else None,
                "p99": round(sorted(lookup_ms)[int(0.99 * len(lookup_ms)) - 1], 3) if lookup_ms else None,
                "max": round(max(lookup_ms), 3) if lookup_ms else None,
            },
        }
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())