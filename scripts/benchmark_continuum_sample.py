"""Sample-v1 Continuum benchmark runner (founder side).

Loads the sample question manifest, runs the layered Continuum pipeline,
and writes question-level results + a comparison-friendly report.

The official scoring lives on the teammate's benchmark runner; this script
produces the Continuum-side results and diagnostics ONLY.

Usage:
    python scripts/benchmark_continuum_sample.py [--questions FILE] [--report-out DIR]
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from continuum.benchmark import answer_many
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = ROOT / "data" / "labels" / "eval-questions.jsonl"
DEFAULT_OUT = ROOT / "data" / "metadata" / "benchmark_continuum_sample"


def main(questions_path: Path, out_dir: Path) -> dict:
    questions = [json.loads(line) for line in questions_path.open(encoding="utf-8") if line.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)

    with HydraDBClient() as client:
        store = EntityStore(client)
        results = answer_many(client, questions, entity_store=store)

    per_question = {r["question_id"]: r for r in results}
    (out_dir / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results),
        encoding="utf-8",
    )
    (out_dir / "report.json").write_text(
        json.dumps(_report(results), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return _report(results)


def _report(results: list[dict]) -> dict:
    latencies = [r["latency_ms"]["total"] for r in results if r["latency_ms"]["total"]]
    statuses = {}
    for r in results:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    context = {
        "artifacts": sum(r["context"]["artifacts"] for r in results),
        "characters": sum(r["context"]["characters"] for r in results),
        "claims": sum(r["context"]["claims"] for r in results),
        "evidence_items": sum(r["context"]["evidence_items"] for r in results),
    }
    return {
        "gate": "benchmark-continuum-sample",
        "questions": len(results),
        "status_distribution": statuses,
        "latency_ms": {
            "p50": round(statistics.median(latencies), 2) if latencies else 0,
            "max": round(max(latencies), 2) if latencies else 0,
        },
        "context_totals": context,
        "question_ids": [r["question_id"] for r in results],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = main(args.questions, args.report_out)
    print(json.dumps(report, indent=2))
