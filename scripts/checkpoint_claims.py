"""Gate 2 checkpoint: classify and load the teammate's top-50 extracted claims.

The checkpoint answers: "can real extraction output enter the graph?"
Every claim is classified at each gate (contract -> artifact present ->
mentions resolvable -> timestamp resolvable), the passing subset is loaded
into HydraDB, and the load is verified by read-back.

A claim that fails any gate is NOT loaded — it is reported with its reason.
This is the founder-side verification the teammate's PR depends on.

Usage:
    python scripts/checkpoint_claims.py [--reset] [--claims FILE] [--resolutions FILE]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from continuum.claims import ContractError, load_claims, validate_claim
from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import READ_DSID_ARTIFACTS, load_claims as load_claims_graph
from continuum.query import resolve_state

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLAIMS = ROOT / "data" / "extraction" / "claims_checkpoint50.jsonl"
DEFAULT_RESOLUTIONS = ROOT / "data" / "fixtures" / "phase2b" / "resolutions-checkpoint50.json"


def main(claims_path: Path, resolutions_path: Path, reset: bool = False) -> dict:
    resolutions = json.loads(resolutions_path.read_text(encoding="utf-8"))
    resolvable = {
        mention: entity_key
        for entity_key, definition in resolutions.items()
        for mention in definition.get("mentions", [])
    }

    with HydraDBClient() as client:
        dsid_artifacts = {row["dsid"]: row for row in client.execute(READ_DSID_ARTIFACTS).rows}
        artifact_time = {row["dsid"]: row.get("timestamp") for row in dsid_artifacts.values()}

        failures: dict[str, str] = {}
        passing: list[dict] = []
        for line_number, line in enumerate(claims_path.open(encoding="utf-8"), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                claim = validate_claim(json.loads(line))
            except ContractError as exc:
                failures[line_number] = f"contract: {exc}"
                continue
            if claim.artifact_id not in dsid_artifacts:
                failures[claim.claim_id] = f"artifact_not_in_graph: {claim.artifact_id}"
                continue
            for side, mention in (("subject", claim.subject_mention), ("object", claim.object_mention)):
                if mention not in resolvable:
                    failures[claim.claim_id] = f"unresolvable_{side}_mention: {mention[:80]!r}"
                    break
            else:
                if not (claim.observed_at or artifact_time.get(claim.artifact_id)):
                    failures[claim.claim_id] = "no_timestamp: claim has null observed_at and artifact has no timestamp"
                    continue
                passing.append(claim)

        report = {
            "gate": "checkpoint50",
            "claims_attempted": len(passing) + len(failures),
            "claims_loaded": len(passing),
            "claims_rejected": len(failures),
            "rejection_reasons": dict(Counter(reason.split(":")[0] for reason in failures.values())),
            "rejected_claims": failures,
        }

        if passing:
            result = load_claims_graph(
                client,
                claims=passing,
                resolutions=resolutions,
                reset=reset,
            )
            report["load"] = {
                "claims_attempted": result.claims_attempted,
                "claims_written": result.claims_written,
                "read_back_count": result.read_back_count,
                "mismatches": result.mismatches,
                "relationships": result.relationships,
                "load_ms": round(result.load_ms, 2),
            }
            report["loaded_claims"] = [
                {
                    "claim_id": claim.claim_id,
                    "predicate": claim.predicate,
                    "subject": claim.subject_mention,
                    "object": claim.object_mention,
                    "subject_id": resolvable[claim.subject_mention],
                    "object_id": resolvable[claim.object_mention],
                }
                for claim in passing
            ]
        else:
            report["load"] = None
            report["loaded_claims"] = []
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument("--resolutions", type=Path, default=DEFAULT_RESOLUTIONS)
    args = parser.parse_args()
    report = main(args.claims, args.resolutions, reset=args.reset)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    output = ROOT / "data" / "metadata" / "checkpoint50_report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {output}")
