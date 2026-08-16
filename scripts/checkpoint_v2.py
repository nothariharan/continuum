"""Checkpoint v2: layered extraction-quality report (founder extraction-v2).

Replaces the old single-number 0/50 gate with the four-layer view:

    lexicon coverage        artifacts that mention >=1 lexicon entity
    candidate pair coverage artifacts with >=1 person AND >=1 account
    relation extraction     claims produced by deterministic v2 patterns
    graph-loadable          claims that pass the canonical checkpoint gate

Also reports relation precision/recall against the known-good fixture
(data/fixtures/phase2b_real_claims.jsonl) on the artifacts it covers, and
stage latencies. Does NOT modify continuum/hydradb/claims.py or the state
engine — graph-loadability reuses checkpoint_claims.classify_claim verbatim.

Usage:
    python scripts/checkpoint_v2.py [--subset 11|all] [--lexicon FILE] [--claims-out FILE]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from time import perf_counter

from continuum.dataset.artifact import Artifact
from continuum.extract.v2.candidates import find_candidates
from continuum.extract.v2.pipeline import run_pipeline
from continuum.extract.v2.relations import extract_relations

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_LEXICON = ROOT / "data" / "fixtures" / "phase2b" / "extraction-eval-lexicon.json"
DEFAULT_FIXTURE = ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"
DEFAULT_CLAIMS_OUT = ROOT / "data" / "extraction" / "claims_v2.jsonl"
DEFAULT_REPORT_OUT = ROOT / "data" / "metadata" / "checkpoint_v2_report.json"

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


def load_artifacts(path: Path, subset: str) -> list[Artifact]:
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    if subset == "11":
        by_id = {row["id"]: row for row in rows}
        rows = [by_id[a_id] for a_id in KNOWN_PAIR_ARTIFACTS if a_id in by_id]
    return [
        Artifact(
            id=row["id"],
            source=row["source"],
            source_id=row["source_id"],
            type=row["type"],
            author=row.get("author"),
            timestamp=row.get("timestamp"),
            title=row.get("title"),
            content=row["content"],
            metadata=row.get("metadata") or {},
        )
        for row in rows
    ]


def load_lexicon(path: Path) -> dict:
    """The eval lexicon is wrapped in {meta, entities}; unwrap it."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "entities" in payload:
        return payload["entities"]
    return payload


def load_fixture(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def fixture_key(claim: dict) -> tuple[str, str, str, str]:
    return (
        claim["artifact_id"],
        str(claim.get("subject_mention", "")).strip().lower(),
        str(claim.get("predicate", "")),
        str(claim.get("object_mention", "")).strip().lower(),
    )


def main(subset: str, lexicon_path: Path, claims_out: Path | None, report_out: Path) -> dict:
    lexicon = load_lexicon(lexicon_path)
    artifacts = load_artifacts(DEFAULT_SAMPLE, subset)

    started = perf_counter()
    pipeline = run_pipeline(artifacts, lexicon)
    pipeline_ms = (perf_counter() - started) * 1000

    claims = []
    for detail in pipeline["detail"]:
        claims.extend(detail["relations"])
    if claims_out:
        from continuum.extract.v2.pipeline import write_claims_jsonl

        write_claims_jsonl(claims, claims_out)

    # graph-loadability via the canonical gate (HydraDB artifact timestamps)
    from continuum.hydradb import HydraDBClient
    from continuum.hydradb.claims import READ_DSID_ARTIFACTS

    import importlib.util

    _spec = importlib.util.spec_from_file_location(
        "checkpoint_claims", ROOT / "scripts" / "checkpoint_claims.py"
    )
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    classify_claim = _module.classify_claim

    resolutions_map = {
        mention: entity_key
        for entity_key, definition in lexicon.items()
        for mention in definition.get("mentions", [])
    }
    entity_labels = {key: definition["label"] for key, definition in lexicon.items()}

    with HydraDBClient() as client:
        dsid_artifacts = {row["dsid"]: row for row in client.execute(READ_DSID_ARTIFACTS).rows}
        artifact_time = {row["dsid"]: row.get("timestamp") for row in dsid_artifacts.values()}

        verdicts = []
        for claim in claims:
            verdict = classify_claim(claim, resolutions_map, entity_labels, artifact_time)
            verdicts.append({**verdict, "claim_id": claim["claim_id"], "predicate": claim["predicate"]})

    graph_pass = [v for v in verdicts if v["status"] == "PASS"]
    graph_fail = Counter(v["status"] for v in verdicts if v["status"] != "PASS")

    # precision/recall against the known-good fixture
    fixture = load_fixture(DEFAULT_FIXTURE)
    fixture_claims = [f for f in fixture if f["artifact_id"] in {a.id for a in artifacts}]
    fixture_keys = {fixture_key(f) for f in fixture_claims}
    extracted_keys = {fixture_key(c) for c in claims}

    matched = extracted_keys & fixture_keys
    precision = len(matched) / len(extracted_keys) if extracted_keys else None
    recall = len(matched) / len(fixture_keys) if fixture_keys else None

    report = {
        "gate": "extraction-v2-checkpoint",
        "lexicon": str(lexicon_path),
        "subset": subset,
        "layers": {
            "lexicon_coverage": {
                "artifacts": pipeline["artifacts"],
                "with_candidates": pipeline["with_candidates"],
                "coverage_rate": round(pipeline["with_candidates"] / pipeline["artifacts"], 3),
            },
            "candidate_pair_coverage": {
                "with_pair": pipeline["with_pair"],
                "pair_rate": round(pipeline["with_pair"] / pipeline["artifacts"], 3),
            },
            "relation_extraction": {
                "claims": len(claims),
                "by_predicate": pipeline["claims_by_predicate"],
                "artifacts_with_claims": sum(1 for d in pipeline["detail"] if d["relations"]),
            },
            "graph_loadable": {
                "passed": len(graph_pass),
                "failed": len(verdicts) - len(graph_pass),
                "failure_summary": dict(graph_fail),
            },
            "fixture_eval": {
                "fixture_claims": len(fixture_claims),
                "fixture_keys": len(fixture_keys),
                "extracted_claims": len(claims),
                "matched": len(matched),
                "precision": round(precision, 3) if precision is not None else None,
                "recall": round(recall, 3) if recall is not None else None,
            },
        },
        "latency_ms": {
            "pipeline_total": round(pipeline_ms, 1),
            "per_artifact": round(pipeline_ms / max(len(artifacts), 1), 2),
        },
        "detail": [
            {
                "artifact_id": d["artifact_id"],
                "source": d["source"],
                "candidates": d["candidates"],
                "pair": d["pair"],
                "claims": [
                    {
                        "claim_id": c["claim_id"],
                        "predicate": c["predicate"],
                        "subject": c["subject_mention"],
                        "object": c["object_mention"],
                        "evidence": c["evidence_span"][:120],
                        "observed_at": c["observed_at"],
                    }
                    for c in d["relations"]
                ],
            }
            for d in pipeline["detail"]
        ],
        "graph_verdicts": verdicts,
    }
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", choices=["11", "all"], default="11")
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    parser.add_argument("--claims-out", type=Path, default=DEFAULT_CLAIMS_OUT)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_OUT)
    args = parser.parse_args()

    report = main(args.subset, args.lexicon, args.claims_out, args.report_out)
    layers = report["layers"]
    print("lexicon coverage      :", layers["lexicon_coverage"])
    print("candidate pair coverage:", layers["candidate_pair_coverage"])
    print("relation extraction   :", layers["relation_extraction"])
    print("graph-loadable        :", layers["graph_loadable"])
    print("fixture eval          :", layers["fixture_eval"])
    print("latency_ms            :", report["latency_ms"])
