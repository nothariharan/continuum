"""End-to-end real-claims pipeline: fixture -> validate -> load -> resolve ->
current state / history / conflict / provenance / abstention -> structured result.

One command (`make real-claims-e2e`) turns any contract-valid claims fixture
into a fully queried HydraDB graph. When the teammate lands new claims:

    python scripts/real_claims_e2e.py \\
        --claims path/to/claims.jsonl --resolutions path/to/resolutions.json --real

No manual wiring needed: real dsid artifacts are auto-loaded if missing, the
claims are validated and loaded, and every (entity, predicate) pair in the
fixture is resolved with the canonical envelope.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from continuum.claims import ContractError, load_claims
from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import (
    READ_DSID_ARTIFACTS,
    count_claims,
    load_claims as load_claims_graph,
    resolve_mentions,
)
from continuum.query import (
    resolve_conflicts,
    resolve_provenance,
    resolve_state,
    resolve_state_on,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLAIMS = ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"
DEFAULT_RESOLUTIONS = ROOT / "data" / "fixtures" / "phase2b" / "resolutions-real.json"
SAMPLE_ARTIFACTS = ROOT / "data" / "samples" / "phase2a-sample.jsonl"


def _ensure_real_artifacts(client: HydraDBClient, claims: list) -> None:
    """Load the Phase 2A sample artifacts when any claim references a missing dsid."""
    present = {row["dsid"] for row in client.execute(READ_DSID_ARTIFACTS).rows}
    needed = {claim.artifact_id for claim in claims if claim.artifact_id.startswith("dsid_")} - present
    if not needed:
        return
    records = [
        json.loads(line)
        for line in SAMPLE_ARTIFACTS.open(encoding="utf-8")
        if line.strip() and json.loads(line)["id"] in needed
    ]
    if not records:
        raise ContractError(f"claims reference dsid artifacts not found in the sample: {sorted(needed)}")
    from continuum.hydradb.artifacts import load_artifacts

    load_artifacts(client, records)


SOURCES = [
    {"key": "source:slack", "name": "Slack"},
    {"key": "source:gmail", "name": "Gmail"},
    {"key": "source:linear", "name": "Linear"},
    {"key": "source:confluence", "name": "Confluence"},
    {"key": "source:fireflies", "name": "Fireflies"},
    {"key": "source:github", "name": "GitHub"},
    {"key": "source:jira", "name": "Jira"},
    {"key": "source:google_drive", "name": "Google Drive"},
    {"key": "source:hubspot", "name": "HubSpot"},
]


def run(claims_path: Path, resolutions_path: Path, real: bool) -> dict:
    claims = load_claims(claims_path)
    resolutions = json.loads(resolutions_path.read_text(encoding="utf-8"))
    entities = resolve_mentions(claims, resolutions)
    entity_keys = sorted(
        {entities[c.subject_mention]["key"] for c in claims}
        | {entities[c.object_mention]["key"] for c in claims}
    )

    with HydraDBClient() as client:
        _ensure_real_artifacts(client, claims)
        result = load_claims_graph(
            client,
            claims=claims,
            resolutions=resolutions,
            fixture_artifacts=[] if real else list(_fixture_artifacts()),
            fixture_sources=[] if real else SOURCES,
            reset=True,
        )

        pairs = defaultdict(list)
        for claim in claims:
            pairs[entities[claim.object_mention]["key"]].append(claim.predicate)

        queries = {"current": [], "historical": [], "conflict": [], "provenance": [], "abstention": []}
        for entity_key in entity_keys:
            predicates = sorted(set(pairs.get(entity_key, [])))
            if not predicates:
                queries["abstention"].append(
                    {"entity_id": entity_key, "result": resolve_state(client, entity_key, "OWNS")}
                )
                continue
            for predicate in predicates:
                queries["current"].append(
                    {"entity_id": entity_key, "predicate": predicate, "result": resolve_state(client, entity_key, predicate)}
                )
                queries["conflict"].append(
                    {"entity_id": entity_key, "predicate": predicate, "result": resolve_conflicts(client, entity_key, predicate)}
                )
                queries["provenance"].append(
                    {"entity_id": entity_key, "predicate": predicate, "result": resolve_provenance(client, entity_key, predicate)}
                )
            earliest = min(c.observed_at or "" for c in claims if entities[c.object_mention]["key"] == entity_key and c.observed_at)
            if earliest:
                before = "1970-01-01" if earliest < "1970-01-02" else (int(earliest[:4]) - 1, earliest[5:10])
                before_date = f"{before[0]}-{before[1]}"
                queries["historical"].append(
                    {
                        "entity_id": entity_key,
                        "predicate": predicates[0],
                        "as_of": before_date,
                        "result": resolve_state_on(client, entity_key, before_date, predicates[0]),
                    }
                )

        def summarize(bucket: list) -> dict:
            ok = all(item["result"].get("status") in ("definitive", "conflict", "consistent", "absent") for item in bucket)
            return {"checks": len(bucket), "passed": ok, "detail": bucket}

        report = {
            "claims": len(claims),
            "entities": len(entity_keys),
            "load": {
                "claims_written": result.claims_written,
                "mismatches": result.mismatches,
                "load_ms": round(result.load_ms, 2),
                "read_back_count": result.read_back_count,
            },
            "queries": {name: summarize(items) for name, items in queries.items()},
        }
    return report


def _fixture_artifacts() -> list[dict]:
    path = ROOT / "data" / "fixtures" / "phase2b" / "artifacts.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-claims end-to-end pipeline")
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument("--resolutions", type=Path, default=DEFAULT_RESOLUTIONS)
    parser.add_argument("--real", action="store_true", help="claims reference real dsid artifacts")
    args = parser.parse_args()

    report = run(args.claims, args.resolutions, real=args.real)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    ok = all(v["passed"] for v in report["queries"].values()) and report["load"]["mismatches"] == 0
    print(f"\nE2E VERDICT: {'PASS' if ok else 'FAIL'}")
    raise SystemExit(0 if ok else 1)
