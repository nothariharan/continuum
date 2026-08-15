"""Measure the query shapes Phase 3 (entity resolution) and future state
queries will need, against the current small graph. No optimization — this
documents which shapes work on this runtime and their latency.

Run: python scripts/measure_query_shapes.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from continuum.hydradb import HydraDBClient

SHAPES = [
    ("candidate_by_exact_key", "MATCH (n {key: $key}) RETURN n.key AS key", {"key": "person:may-patel"}),
    ("candidate_by_id_prop", "MATCH (n:Person {name: $name}) RETURN n.key AS key", {"name": "Maya Patel"}),
    ("candidate_by_external_id", "MATCH (n) WHERE n.aliases CONTAINS $alias RETURN n.key AS key", {"alias": "may-patel"}),
    ("claims_involving_entity", "MATCH (c:Claim {subject_id: $key}) RETURN c.key AS key", {"key": "person:may-patel"}),
    ("claims_about_entity", "MATCH (c:Claim {object_id: $key}) RETURN c.key AS key", {"key": "account:lucentgrid"}),
    ("conflicting_claims", "MATCH (a:Claim {object_id: $key, predicate: $p})-[:CONTRADICTS]->(b:Claim) RETURN a.key AS a, b.key AS b", {"key": "account:acme-health", "p": "OWNS"}),
    ("current_owner", "MATCH (s)-[r:OWNS]->(o {key: $key}) WHERE r.valid_to = $open RETURN s.key AS key", {"key": "account:lucentgrid", "open": "9999-12-31"}),
    ("prior_owner", "MATCH (s)-[r:OWNS]->(o {key: $key}) WHERE r.valid_to <> $open ORDER BY r.valid_from DESC RETURN s.key AS key", {"key": "account:cedarbank", "open": "9999-12-31"}),
    ("reverse_dependencies", "MATCH (s)-[:DEPENDS_ON]->(o {key: $key}) RETURN s.key AS key", {"key": "project:hosted-api"}),
    ("claim_to_artifact", "MATCH (c:Claim {key: $key})-[:SOURCED_FROM]->(a:Artifact)-[:FROM]->(s:Source) RETURN a.key AS a, s.key AS s", {"key": "claim:may-patel-owns-lucentgrid"}),
    ("entity_pair_counts", "MATCH (c:Claim) RETURN c.predicate AS p, count(*) AS n", {}),
    ("two_hop", "MATCH (c:Claim {subject_id: $key})-[:SOURCED_FROM]->(a:Artifact)<-[:SOURCED_FROM]-(d:Claim) RETURN d.key AS key", {"key": "person:may-patel"}),
]


def percentile(values, p):
    values = sorted(values)
    index = (len(values) - 1) * p
    lower, upper = int(index), min(int(index) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def main(iterations: int = 15) -> dict:
    results = {}
    with HydraDBClient() as client:
        for name, query, params in SHAPES:
            samples = []
            ok = True
            for _ in range(iterations):
                started = time.perf_counter()
                try:
                    rows = client.execute(query, params).rows
                except Exception as exc:
                    results[name] = {"error": str(exc)[:160]}
                    ok = False
                    break
                samples.append((time.perf_counter() - started) * 1000)
            if ok:
                results[name] = {
                    "p50_ms": round(percentile(samples, 0.50), 3),
                    "p95_ms": round(percentile(samples, 0.95), 3),
                    "p99_ms": round(percentile(samples, 0.99), 3),
                    "rows": len(rows),
                }
    return results


if __name__ == "__main__":
    results = main()
    print(json.dumps(results, indent=2))
    output = Path("docs/hydradb-query-shape-measurements.json")
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
