"""Predicate refinement experiment — deterministic vs Fireworks refinement.

Runs the 11 known pair artifacts through:

    Mode A  deterministic only                      (baseline)
    Mode B  Fireworks refinement on ambiguous only  (email-thread, AE-label, slack-csm)
    Mode C  Fireworks refinement on every claim

Reports per artifact: deterministic predicate, refined predicate, expected
fixture predicate, confidence, latency. Aggregates: exact-match, predicate
accuracy, graph-loadability, false positives, model-call rate, latency.

Does not modify HydraDB, the state engine, or the shared contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from continuum.dataset.artifact import Artifact
from continuum.extract.v2.candidates import find_candidates
from continuum.extract.v2.pipeline import refine_ambiguous_claims
from continuum.extract.v2.refinement import create_refinement_provider
from continuum.extract.v2.relations import extract_relations

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_LEXICON = ROOT / "data" / "fixtures" / "phase2b" / "extraction-eval-lexicon.json"
DEFAULT_FIXTURE = ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"
DEFAULT_REPORT_OUT = ROOT / "data" / "metadata" / "predicate_refinement_experiment.json"

KNOWN_PAIR_ARTIFACTS = [
    "dsid_58652f7aa95b4191bdfe69b5ab6185ce",
    "dsid_418f38fa389c47e497463e221751c685",
    "dsid_632713f6e1a745abb4a8ebb6da6f1dd8",
    "dsid_b5d97257992a4f618c90df006e2e90a8",
    "dsid_86d691cee0b548bcb22d8428dc7b6ce7",
    "dsid_ac80b52fe541428292143997399615e5",
    "dsid_faac5db76bdb43d399ff09fe6d97f503",
    "dsid_fbdb90b68a2c47369bb5011328e67ec2",
    "dsid_8fb3495571e4429d99184d71090e3828",
    "dsid_2479a77669e042b9b8e5ba51c31e7ea2",
    "dsid_2bdce1fe36d941f091b28044b24d86e3",
]


def claim_key(claim: dict) -> tuple[str, str, str, str]:
    return (
        claim["artifact_id"],
        str(claim.get("subject_mention", "")).strip().lower(),
        str(claim.get("predicate", "")),
        str(claim.get("object_mention", "")).strip().lower(),
    )


def main(model: str, report_out: Path) -> dict:
    from continuum.extract.llm_client import load_local_env

    load_local_env()
    lexicon_payload = json.loads(DEFAULT_LEXICON.read_text(encoding="utf-8"))
    lexicon = lexicon_payload["entities"] if "entities" in lexicon_payload else lexicon_payload

    rows = [json.loads(line) for line in DEFAULT_SAMPLE.open(encoding="utf-8") if line.strip()]
    by_id = {row["id"]: row for row in rows}
    artifacts = []
    for artifact_id in KNOWN_PAIR_ARTIFACTS:
        row = by_id.get(artifact_id)
        if row:
            artifacts.append(
                Artifact(
                    id=row["id"], source=row["source"], source_id=row["source_id"],
                    type=row["type"], author=row.get("author"), timestamp=row.get("timestamp"),
                    title=row.get("title"), content=row["content"], metadata=row.get("metadata") or {},
                )
            )

    fixture = [json.loads(line) for line in DEFAULT_FIXTURE.open(encoding="utf-8") if line.strip()]
    fixture_keys = {claim_key(f) for f in fixture}

    # deterministic extraction over the 11 artifacts
    claims = []
    det_ms = 0.0
    for artifact in artifacts:
        started = perf_counter()
        candidates = find_candidates(artifact, lexicon)
        rels = extract_relations(artifact, candidates, lexicon)
        det_ms += (perf_counter() - started) * 1000
        claims.extend(rels)
    det_latency = det_ms / max(len(artifacts), 1)

    def evaluate(label: str, claim_list: list[dict], calls: int, model_ms: float) -> dict:
        keys = {claim_key(c) for c in claim_list}
        matched = keys & fixture_keys
        return {
            "mode": label,
            "claims": len(claim_list),
            "exact_match": len(matched),
            "precision": round(len(matched) / len(keys), 3) if keys else None,
            "recall": round(len(matched) / len(fixture_keys), 3),
            "model_calls": calls,
            "model_calls_per_artifact": round(calls / max(len(artifacts), 1), 2),
            "model_latency_ms": round(model_ms, 1),
            "total_latency_ms_per_artifact": round(det_latency + model_ms / max(len(artifacts), 1), 2),
        }

    # Mode A — deterministic only
    mode_a = evaluate("A-deterministic", claims, 0, 0.0)

    # Mode B — Fireworks on ambiguous only
    provider_b = create_refinement_provider("fireworks", model=model)
    started = perf_counter()
    refined_b = refine_ambiguous_claims(
        claims, provider_b, lexicon, mode="ambiguous", artifacts={a.id: a for a in artifacts}
    )
    model_ms_b = (perf_counter() - started) * 1000
    mode_b = evaluate("B-refine-ambiguous", refined_b["claims"], refined_b["calls"], model_ms_b)

    # Mode C — Fireworks on every claim
    provider_c = create_refinement_provider("fireworks", model=model)
    started = perf_counter()
    refined_c = refine_ambiguous_claims(
        claims, provider_c, lexicon, mode="all", artifacts={a.id: a for a in artifacts}
    )
    model_ms_c = (perf_counter() - started) * 1000
    mode_c = evaluate("C-refine-all", refined_c["claims"], refined_c["calls"], model_ms_c)

    per_claim = []
    for item in refined_b["per_claim"]:
        expected = next(
            (f for f in fixture
             if f["artifact_id"] == item["artifact_id"]
             and f["subject_mention"].strip().lower() == item["subject"].strip().lower()
             and f["object_mention"].strip().lower() == item["object"].strip().lower()),
            None,
        )
        per_claim.append({
            **item,
            "expected_predicate": expected["predicate"] if expected else None,
            "exact": (
                expected is not None
                and item["final_predicate"] == expected["predicate"]
                and not item["abstained"]
            ),
        })

    report = {
        "gate": "predicate-refinement-experiment",
        "model": model,
        "artifacts": len(artifacts),
        "fixture_claims": len(fixture_keys),
        "deterministic_latency_ms_per_artifact": round(det_latency, 2),
        "modes": {"A": mode_a, "B": mode_b, "C": mode_c},
        "per_claim": per_claim,
    }
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="Fireworks model id override")
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_OUT)
    args = parser.parse_args()

    report = main(args.model, args.report_out)
    print(f"model: {report['model']}  artifacts: {report['artifacts']}  fixture: {report['fixture_claims']}")
    print(f"deterministic latency: {report['deterministic_latency_ms_per_artifact']} ms/artifact")
    for label, mode in report["modes"].items():
        print(f"  Mode {label:<22} claims={mode['claims']:<3} exact={mode['exact_match']:<3} "
              f"precision={mode['precision']} recall={mode['recall']} calls={mode['model_calls']} "
              f"model_ms={mode['model_latency_ms']}")
    print()
    for item in report["per_claim"]:
        print(f"  {item['subject'][:18]:<20} {item['candidate_predicate']:<13} -> {item['final_predicate']:<13} "
              f"expected={str(item['expected_predicate']):<13} {'OK' if item['exact'] else 'MISS'}"
              f"  conf={item['confidence']:.2f} {item['latency_ms']}ms")
