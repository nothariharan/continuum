"""Evaluate mention/claim extraction against ground-truth labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.dataset.artifact import Artifact
from continuum.eval.ground_truth import load_ground_truth
from continuum.eval.metrics import aggregate_scores, score_by_predicate, score_claims, score_mentions
from continuum.extract.claim import extract_claims
from continuum.extract.llm_client import load_local_env
from continuum.extract.mention import extract_mentions
from continuum.extract.schemas import artifacts_from_dicts, load_artifacts_jsonl

DEFAULT_LABELS = Path(__file__).resolve().parents[1] / "data" / "labels" / "phase2b-ground-truth.jsonl"
DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "metadata" / "extraction_metrics.json"


def evaluate_strategy(
    artifacts: list[Artifact],
    labels: list,
    method: str,
) -> dict:
    label_ids = {record.artifact_id for record in labels}
    subset = [a for a in artifacts if a.id in label_ids]
    mentions = extract_mentions(subset, method=method)
    claims = extract_claims(subset, method=method)

    mention_rows = []
    claim_rows = []
    for record in labels:
        gold_mentions = record.mentions
        gold_claims = record.claims
        pred_mentions = [m for m in mentions if m.artifact_id == record.artifact_id]
        pred_claims = [c for c in claims if c.artifact_id == record.artifact_id]
        if gold_mentions:
            mention_rows.append(score_mentions(pred_mentions, gold_mentions, artifact_id=record.artifact_id))
        if gold_claims:
            claim_rows.append(score_claims(pred_claims, gold_claims, artifact_id=record.artifact_id))

    gold_records = [{"artifact_id": r.artifact_id, "claims": r.claims} for r in labels]
    return {
        "mention": aggregate_scores(mention_rows),
        "claim": aggregate_scores(claim_rows),
        "claim_by_predicate": score_by_predicate(claims, gold_records),
        "artifacts_evaluated": len(labels),
        "mentions_extracted": len(mentions),
        "claims_extracted": len(claims),
    }


def main() -> int:
    load_local_env()
    parser = argparse.ArgumentParser(description="Evaluate extraction strategies")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--strategies",
        default="deterministic,hybrid",
        help="comma-separated: deterministic, hybrid, llm (llm is slow on full label set)",
    )
    args = parser.parse_args()

    labels = load_ground_truth(args.labels)
    rows = load_artifacts_jsonl(args.sample)
    artifacts = artifacts_from_dicts(rows)

    strategies = {}
    for method in [s.strip() for s in args.strategies.split(",") if s.strip()]:
        print(f"evaluating strategy: {method}", flush=True)
        strategies[method] = evaluate_strategy(artifacts, labels, method)

    payload = {
        "label_set_size": len(labels),
        "strategies": strategies,
        "notes": "deterministic preferred; llm/hybrid require FIREWORKS_API_KEY or OPENAI_API_KEY",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
