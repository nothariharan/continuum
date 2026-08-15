"""Claim-handoff verifier: the founder's feedback loop to the extraction side.

For every candidate claim in claims.jsonl, classify why it can or cannot
enter the graph. Codes:

- MALFORMED_ID           claim_id / artifact_id does not match the contract
- INVALID_SUBJECT        subject mention empty, or not manually resolvable
- INVALID_OBJECT         object mention empty, or not manually resolvable
- INVALID_PREDICATE      predicate outside the supported vocabulary
- MISSING_ARTIFACT       artifact_id not present in the HydraDB graph
- INVALID_TIMESTAMP      timestamp present but not a real ISO date (or
                         valid_to < valid_from)
- MISSING_TIMESTAMP      no observed_at AND the artifact has no timestamp
- UNSUPPORTED_ENTITY_PAIR subject/object resolve, but the resolved label
                         pair is not canonical for the predicate
- CONTRACT_VIOLATION     anything else the canonical validator rejects
                         (confidence, evidence_span, extraction_method)

"Graph-loadable" means Continuum can represent the claim without inventing
entities, inventing timestamps, or violating the canonical predicate/entity
constraints. This script encodes that; it does not rely on human judgment.

Usage:
    python scripts/checkpoint_claims.py [--claims FILE] [--resolutions FILE] [--load]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from continuum.claims import (
    SUPPORTED_PREDICATES,
    ContractError,
    validate_claim,
)
from continuum.claims.schema import ARTIFACT_ID_RE, CLAIM_ID_RE
from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import READ_DSID_ARTIFACTS, load_claims as load_claims_graph, pair_supported, resolve_mentions

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLAIMS = ROOT / "data" / "extraction" / "claims.jsonl"
DEFAULT_RESOLUTIONS = ROOT / "data" / "fixtures" / "phase2b" / "resolutions-checkpoint50.json"

MALFORMED_ID = "MALFORMED_ID"
INVALID_SUBJECT = "INVALID_SUBJECT"
INVALID_OBJECT = "INVALID_OBJECT"
INVALID_PREDICATE = "INVALID_PREDICATE"
MISSING_ARTIFACT = "MISSING_ARTIFACT"
INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
MISSING_TIMESTAMP = "MISSING_TIMESTAMP"
UNSUPPORTED_ENTITY_PAIR = "UNSUPPORTED_ENTITY_PAIR"
CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
PASS = "PASS"


def _is_iso(value: str) -> bool:
    from datetime import datetime

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def classify_claim(
    record: dict,
    resolvable: dict[str, str],
    entity_labels: dict[str, str],
    artifact_time: dict[str, str | None],
) -> dict:
    claim_id = str(record.get("claim_id", ""))
    artifact_id = str(record.get("artifact_id", ""))
    if CLAIM_ID_RE.match(claim_id) is None or ARTIFACT_ID_RE.match(artifact_id) is None:
        return {"status": MALFORMED_ID, "reason": f"claim_id={claim_id!r} artifact_id={artifact_id!r}"}

    subject = record.get("subject_mention")
    object_ = record.get("object_mention")
    if not (isinstance(subject, str) and subject.strip()):
        return {"status": INVALID_SUBJECT, "reason": "empty or non-string subject_mention"}
    if not (isinstance(object_, str) and object_.strip()):
        return {"status": INVALID_OBJECT, "reason": "empty or non-string object_mention"}

    predicate = str(record.get("predicate", ""))
    if predicate not in SUPPORTED_PREDICATES:
        return {
            "status": INVALID_PREDICATE,
            "reason": f"predicate={predicate!r} not in {sorted(SUPPORTED_PREDICATES)}",
        }

    for field in ("observed_at", "valid_from", "valid_to"):
        value = record.get(field)
        if value is not None and not (isinstance(value, str) and _is_iso(value)):
            return {"status": INVALID_TIMESTAMP, "reason": f"{field}={value!r} is not a real ISO date"}
    if (
        record.get("valid_from")
        and record.get("valid_to")
        and str(record["valid_to"])[:10] < str(record["valid_from"])[:10]
    ):
        return {"status": INVALID_TIMESTAMP, "reason": "valid_to earlier than valid_from"}

    observed = record.get("observed_at")
    fallback = artifact_time.get(artifact_id)
    if not observed and not fallback:
        return {
            "status": MISSING_TIMESTAMP,
            "reason": "observed_at is null and the artifact has no timestamp",
        }

    if artifact_id not in artifact_time:
        return {"status": MISSING_ARTIFACT, "reason": f"artifact {artifact_id} not present in the graph"}

    for side, mention in (("subject", subject.strip()), ("object", object_.strip())):
        if mention not in resolvable:
            code = INVALID_SUBJECT if side == "subject" else INVALID_OBJECT
            return {
                "status": code,
                "reason": f"mention {mention[:80]!r} has no manual resolution "
                "(not a resolvable entity name)",
            }

    subject_label = entity_labels[resolvable[subject.strip()]]
    object_label = entity_labels[resolvable[object_.strip()]]
    if not pair_supported(predicate, subject_label, object_label):
        return {
            "status": UNSUPPORTED_ENTITY_PAIR,
            "reason": f"{predicate} ({subject_label} -> {object_label}) is not canonical",
        }

    try:
        validate_claim(record)
    except ContractError as exc:
        return {"status": CONTRACT_VIOLATION, "reason": str(exc)}

    return {
        "status": PASS,
        "reason": "graph-loadable",
        "subject_id": resolvable[subject.strip()],
        "object_id": resolvable[object_.strip()],
        "timestamp_source": "claim" if observed else "artifact",
    }


def main(claims_path: Path, resolutions_path: Path, do_load: bool = False) -> dict:
    resolutions = json.loads(resolutions_path.read_text(encoding="utf-8"))
    resolvable = {
        mention: entity_key
        for entity_key, definition in resolutions.items()
        for mention in definition.get("mentions", [])
    }
    entity_labels = {key: definition["label"] for key, definition in resolutions.items()}

    records = []
    for line_number, line in enumerate(claims_path.open(encoding="utf-8"), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            records.append({"claim_id": f"line {line_number}", "status": MALFORMED_ID, "reason": f"invalid JSON: {exc}"})
            continue
        records.append({"claim_id": str(record.get("claim_id", f"line {line_number}")), "raw": record})

    with HydraDBClient() as client:
        dsid_artifacts = {row["dsid"]: row for row in client.execute(READ_DSID_ARTIFACTS).rows}
        artifact_time = {row["dsid"]: row.get("timestamp") for row in dsid_artifacts.values()}

        verdicts = []
        passing = []
        for item in records:
            if "raw" not in item:
                verdicts.append(item)
                continue
            verdict = classify_claim(item["raw"], resolvable, entity_labels, artifact_time)
            verdict = {
                "claim_id": item["claim_id"],
                "status": verdict["status"],
                "reason": verdict["reason"],
                "predicate": item["raw"].get("predicate"),
                "subject": item["raw"].get("subject_mention"),
                "object": item["raw"].get("object_mention"),
                **(
                    {"subject_id": verdict["subject_id"], "object_id": verdict["object_id"], "timestamp_source": verdict["timestamp_source"]}
                    if verdict["status"] == PASS
                    else {}
                ),
            }
            verdicts.append(verdict)
            if verdict["status"] == PASS:
                passing.append(item["raw"])

        load = None
        if do_load and passing:
            result = load_claims_graph(
                client,
                claims=[validate_claim(record) for record in passing],
                resolutions=resolutions,
                reset=True,
            )
            load = {
                "claims_attempted": result.claims_attempted,
                "claims_written": result.claims_written,
                "mismatches": result.mismatches,
                "relationships": result.relationships,
                "load_ms": round(result.load_ms, 2),
            }

    summary = Counter(v["status"] for v in verdicts)
    return {
        "gate": "claim-handoff",
        "claims_path": str(claims_path),
        "claims_attempted": len(verdicts),
        "passed": summary.get(PASS, 0),
        "failed": len(verdicts) - summary.get(PASS, 0),
        "failure_summary": {k: v for k, v in summary.items() if k != PASS},
        "load": load,
        "claims": verdicts,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claim-handoff verifier")
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument("--resolutions", type=Path, default=DEFAULT_RESOLUTIONS)
    parser.add_argument("--load", action="store_true", help="load the passing claims into HydraDB")
    parser.add_argument(
        "--detail",
        type=int,
        default=20,
        help="max per-claim failure lines on the console (0 = none; report JSON always has all)",
    )
    args = parser.parse_args()

    report = main(args.claims, args.resolutions, do_load=args.load)

    output = ROOT / "data" / "metadata" / "claim_handoff_report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def emit(line: str) -> None:
        try:
            print(line, flush=True)
        except BrokenPipeError:
            # Windows: a consumer that closed the pipe early (e.g.
            # `Select-Object -First N`) must not hang the process.
            try:
                import sys

                sys.stdout.close()
            except Exception:
                pass
            raise SystemExit(0)

    emit(json.dumps({k: v for k, v in report.items() if k != "claims"}, indent=2, ensure_ascii=False))
    if args.detail:
        emit(f"\nfailure detail (first {args.detail} of {len(report['claims'])}):")
        shown = 0
        for verdict in report["claims"]:
            if verdict["status"] == PASS:
                continue
            emit(
                f"  [{verdict['status']:<24}] {verdict['claim_id']} "
                f"{verdict.get('predicate', '')} {str(verdict.get('subject', ''))[:40]!r} -> "
                f"{str(verdict.get('object', ''))[:40]!r} | {verdict['reason'][:90]}"
            )
            shown += 1
            if shown >= args.detail:
                break
    emit(f"\nwrote {output}")
