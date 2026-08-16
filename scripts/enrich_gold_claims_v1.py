"""Enrich Gold Benchmark v1 claim labels from hand-validated real-claim fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.eval.gold_v1 import (
    DEFAULT_GOLD_ROOT,
    GoldClaimRow,
    load_gold_benchmark,
    validate_gold_benchmark,
    write_gold_benchmark,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"


def enrich_from_fixture(benchmark, fixture_path: Path):
    artifact_ids = benchmark.artifact_ids
    existing = {
        (row.artifact_id, row.subject, row.predicate, row.object)
        for row in benchmark.claims
    }
    added = 0
    claims = list(benchmark.claims)
    ambiguities = [row for row in benchmark.ambiguities if row.status != "NO_CLAIM" or row.artifact_id not in artifact_ids]

    for line in fixture_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        artifact_id = row.get("artifact_id")
        if artifact_id not in artifact_ids:
            continue
        key = (artifact_id, row["subject_mention"], row["predicate"], row["object_mention"])
        if key in existing:
            continue
        claims.append(
            GoldClaimRow(
                artifact_id=artifact_id,
                subject=row["subject_mention"],
                subject_type="person" if " " in row["subject_mention"] else "account",
                predicate=row["predicate"],
                object=row["object_mention"],
                object_type="account" if row["predicate"] in {"OWNS", "MAINTAINS"} else "project",
                evidence_span=row.get("evidence_span", ""),
                observed_at=row.get("observed_at"),
                valid_from=row.get("valid_from"),
                valid_to=row.get("valid_to"),
                status="VALID",
                notes="seeded from phase2b_real_claims.jsonl",
                difficulty_tags=("ownership",),
            )
        )
        existing.add(key)
        added += 1
        ambiguities = [a for a in ambiguities if not (a.artifact_id == artifact_id and a.status == "NO_CLAIM")]

    benchmark.claims = claims
    benchmark.ambiguities = ambiguities
    benchmark.manifest["claim_count"] = len(claims)
    benchmark.manifest["ambiguity_count"] = len(ambiguities)
    benchmark.manifest["claim_label_seed"] = str(fixture_path)
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich gold v1 claim labels")
    parser.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    benchmark = load_gold_benchmark(args.gold_root)
    added = enrich_from_fixture(benchmark, args.fixture)
    errors = validate_gold_benchmark(benchmark)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    write_gold_benchmark(benchmark, args.gold_root)
    print(json.dumps({"ok": True, "claims_added": added, "claim_count": len(benchmark.claims)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
