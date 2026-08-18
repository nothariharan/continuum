#!/usr/bin/env python3
"""Run the Slack/Gmail source → answer end-to-end vertical."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.hydradb import HydraDBClient
from continuum.pipeline.source_e2e import SourceE2EPipeline

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "data" / "ground_truth" / "source-e2e-v1"
REPORT_DIR = ROOT / "data" / "metadata"


def main() -> int:
    parser = argparse.ArgumentParser(description="Source fixture → extract → graph → answer E2E")
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--refinement", choices=("mock", "fireworks", "auto"), default="mock")
    parser.add_argument("--fireworks-answer", action="store_true")
    parser.add_argument("--fireworks-budget", type=int, default=20)
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--skip-graph", action="store_true")
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()

    pipeline = SourceE2EPipeline(
        args.gold_dir,
        refinement_provider=args.refinement,
        fireworks_answer=args.fireworks_answer,
        fireworks_budget=args.fireworks_budget,
        model=args.model,
    )

    client = None
    if not args.skip_graph:
        client = HydraDBClient()
        client.__enter__()
        client.health_check()

    try:
        result = pipeline.run(client, load_graph=not args.skip_graph)
    finally:
        if client is not None:
            client.__exit__(None, None, None)

    args.report_dir.mkdir(parents=True, exist_ok=True)
    extraction_report = {
        "commit_sha": result.commit_sha,
        "metrics": result.extraction_metrics,
        "loadable_claims": len(result.loadable_claims),
        "rejected_claims": len(result.rejected_claims),
    }
    fireworks_report = result.fireworks
    latency_report = {
        "commit_sha": result.commit_sha,
        "stages_ms": result.latency_ms,
        "fireworks_calls": result.fireworks.get("calls_used"),
    }
    failure_report = {
        "commit_sha": result.commit_sha,
        "taxonomy": result.failure_taxonomy,
        "question_results": result.question_results,
    }

    (args.report_dir / "source_e2e_extraction_report.json").write_text(
        json.dumps(extraction_report, indent=2) + "\n", encoding="utf-8"
    )
    (args.report_dir / "source_e2e_fireworks_smoke.json").write_text(
        json.dumps(fireworks_report, indent=2) + "\n", encoding="utf-8"
    )
    (args.report_dir / "source_e2e_latency.json").write_text(
        json.dumps(latency_report, indent=2) + "\n", encoding="utf-8"
    )
    (args.report_dir / "source_e2e_failure_taxonomy.json").write_text(
        json.dumps(failure_report, indent=2) + "\n", encoding="utf-8"
    )

    correct = sum(1 for row in result.question_results if row.get("correct"))
    total_q = len(result.question_results)
    summary = {
        "commit_sha": result.commit_sha,
        "artifacts": len(result.artifacts),
        "loadable_claims": len(result.loadable_claims),
        "extraction_precision": result.extraction_metrics.get("precision"),
        "extraction_recall": result.extraction_metrics.get("recall"),
        "questions_correct": f"{correct}/{total_q}",
        "fireworks_calls": result.fireworks.get("calls_used"),
        "latency_ms": result.latency_ms,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
