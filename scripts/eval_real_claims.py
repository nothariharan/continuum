"""Regression/evaluation harness for known-good claim fixtures.

Usage:
    python scripts/eval_real_claims.py [--fixture synthetic|real]

Loads the fixture into HydraDB, then runs scenario checks against expected
values (current state, historical state, provenance, conflict, abstention,
non-OWNS predicates) and reports PASS/FAIL per scenario plus p50/p95/p99
latency. Exit code is non-zero if any scenario fails.

The same harness runs `synthetic` and `real` fixtures without touching the
core query code — extend the SCENARIOS table, not the resolvers.
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


SCENARIOS: dict[str, list[dict]] = {
    "real": [
        {"name": "current_state", "fn": lambda c: resolve_state(c, "account:lucentgrid", "OWNS"), "expect": {"status": "definitive", "value": {"entity_id": "person:may-patel", "name": "Maya Patel"}}},
        {"name": "historical_state", "fn": lambda c: resolve_state_on(c, "account:lucentgrid", "2027-02-11", "OWNS"), "expect": {"status": "definitive", "value": {"entity_id": "person:may-patel", "name": "Maya Patel"}}},
        {"name": "historical_before_evidence", "fn": lambda c: resolve_state_on(c, "account:lucentgrid", "2026-01-01", "OWNS"), "expect": {"status": "absent", "value": None}},
        {"name": "provenance", "fn": lambda c: resolve_provenance(c, "account:acme-health", "OWNS"), "expect": {"status": "definitive", "evidence_len": 2, "source": "gmail", "artifact": "dsid_632713f6e1a745abb4a8ebb6da6f1dd8"}},
        {"name": "conflict", "fn": lambda c: resolve_conflicts(c, "account:acme-health", "OWNS"), "expect": {"status": "conflict", "subjects": ["person:neha-kapoor", "person:priyom-das"]}},
        {"name": "abstention", "fn": lambda c: resolve_state(c, "account:cedarbank", "OWNS"), "expect": {"status": "absent", "value": None}},
        {"name": "maintains_state", "fn": lambda c: resolve_state(c, "account:skyline-systems", "MAINTAINS"), "expect": {"status": "definitive", "value": {"entity_id": "person:ravi-patel", "name": "Ravi Patel"}}},
        {"name": "leads_state", "fn": lambda c: resolve_state(c, "account:skyline-systems", "LEADS"), "expect": {"status": "definitive", "value": {"entity_id": "person:may-chen", "name": "Maya Chen"}}},
        {"name": "assigned_state", "fn": lambda c: resolve_state(c, "account:lucentgrid", "ASSIGNED_TO"), "expect": {"status": "definitive", "value": {"entity_id": "person:ethan-cole", "name": "Ethan Cole"}}},
    ],
    "synthetic": [
        {"name": "current_state", "fn": lambda c: resolve_state(c, "account:cedarbank", "OWNS"), "expect": {"status": "definitive", "value": {"entity_id": "person:camila-reyes", "name": "Camila Reyes"}}},
        {"name": "historical_state", "fn": lambda c: resolve_state_on(c, "account:cedarbank", "2026-06-01", "OWNS"), "expect": {"status": "definitive", "value": {"entity_id": "person:may-patel", "name": "Maya Patel"}}},
        {"name": "provenance", "fn": lambda c: resolve_provenance(c, "account:cedarbank", "OWNS"), "expect": {"status": "definitive", "evidence_len": 3, "sources": {"Gmail", "Slack", "Linear"}}},
        {"name": "conflict", "fn": lambda c: resolve_conflicts(c, "account:cedarbank", "OWNS"), "expect": {"status": "conflict", "subjects": ["person:camila-reyes", "person:may-patel"]}},
        {"name": "abstention", "fn": lambda c: resolve_state(c, "account:orionai", "OWNS"), "expect": {"status": "absent", "value": None}},
        {"name": "maintains_state", "fn": lambda c: resolve_state(c, "project:optimize-conductor", "MAINTAINS"), "expect": {"status": "definitive", "value": {"entity_id": "person:diego-martinez", "name": "Diego Martinez"}}},
    ],
}


def load_fixture(fixture: str) -> None:
    if fixture == "real":
        subprocess.run(
            ["python", str(ROOT / "scripts" / "dataset_load_hydradb.py"), "--reset"],
            check=True, capture_output=True, text=True,
        )
        cmd = [
            "python", str(ROOT / "scripts" / "load_phase2b_claims.py"), "--reset", "--real",
            "--claims", str(ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"),
            "--resolutions", str(ROOT / "data" / "fixtures" / "phase2b" / "resolutions-real.json"),
        ]
    else:
        cmd = ["python", str(ROOT / "scripts" / "load_phase2b_claims.py"), "--reset"]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def check_scenario(result: dict, expect: dict) -> bool:
    if result.get("status") != expect["status"]:
        return False
    if "value" in expect:
        if expect["value"] is None and result.get("value") is not None:
            return False
        if expect["value"] is not None and result.get("value") != expect["value"]:
            return False
    if "evidence_len" in expect and len(result.get("evidence", [])) != expect["evidence_len"]:
        return False
    if "source" in expect and not any(item.get("source") == expect["source"] for item in result.get("evidence", [])):
        return False
    if "sources" in expect and not {item.get("source") for item in result.get("evidence", [])} == expect["sources"]:
        return False
    if "artifact" in expect and not any(item.get("artifact_id") == expect["artifact"] for item in result.get("evidence", [])):
        return False
    if "subjects" in expect and result.get("conflicting_subjects") != expect["subjects"]:
        return False
    return True


def sanitize(value):
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value


def main(fixture: str, iterations: int = 20) -> dict:
    load_fixture(fixture)
    rows = []
    all_pass = True
    with HydraDBClient() as client:
        for scenario in SCENARIOS[fixture]:
            samples = []
            ok = True
            for _ in range(iterations):
                started = time.perf_counter()
                result = scenario["fn"](client)
                samples.append((time.perf_counter() - started) * 1000)
            ok = check_scenario(result, scenario["expect"])
            all_pass = all_pass and ok
            rows.append(
                {
                    "scenario": scenario["name"],
                    "status": "PASS" if ok else "FAIL",
                    "expected": scenario["expect"],
                    "got": {k: result.get(k) for k in ("status", "value", "conflicting_subjects", "evidence")},
                    "p50_ms": round(percentile(samples, 0.50), 3),
                    "p95_ms": round(percentile(samples, 0.95), 3),
                    "p99_ms": round(percentile(samples, 0.99), 3),
                }
            )
    report = {"fixture": fixture, "overall": "PASS" if all_pass else "FAIL", "scenarios": sanitize(rows)}
    output = ROOT / "data" / "metadata" / f"eval_{fixture}_claims.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report, all_pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", choices=["synthetic", "real"], default="real")
    args = parser.parse_args()

    report, all_pass = main(args.fixture)
    width = max(len(row["scenario"]) for row in report["scenarios"])
    print(f"{'scenario':<{width}}  {'status':<6}  {'p50':>7}  {'p95':>7}  {'p99':>7}")
    for row in report["scenarios"]:
        print(f"{row['scenario']:<{width}}  {row['status']:<6}  {row['p50_ms']:>7}  {row['p95_ms']:>7}  {row['p99_ms']:>7}")
    print(f"\nOVERALL: {report['overall']}")
    raise SystemExit(0 if all_pass else 1)
