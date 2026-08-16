"""Sample-v1 Continuum benchmark runner (founder side).

Loads the benchmark foundation's sample-v1 question manifest, runs the
graph-backed Continuum pipeline (continuum.benchmark.answer) over every
question, and writes question-level results + a report.

The official scoring lives on the benchmark foundation runner; this script
produces the Continuum-side results and diagnostics ONLY.

Usage:
    python scripts/benchmark_continuum_sample.py [--mode sample-v1] [--report-out DIR]
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from continuum.benchmark import answer_many
from continuum.entities.store import EntityStore
from continuum.eval.benchmark.schema import load_manifest, load_questions
from continuum.hydradb import HydraDBClient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODE = "sample-v1"
DEFAULT_OUT = ROOT / "data" / "metadata" / "benchmark_continuum_sample"


def main(mode: str, out_dir: Path) -> dict:
    import subprocess
    import sys

    # deterministic fixture load (isolated): 360-artifact sample + real claims
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "dataset_load_hydradb.py"), "--reset"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "load_phase2b_claims.py"), "--reset", "--real",
         "--claims", str(ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"),
         "--resolutions", str(ROOT / "data" / "fixtures" / "phase2b" / "resolutions-real.json")],
        check=True, capture_output=True, text=True,
    )

    manifest = load_manifest(mode)
    questions = load_questions(mode)
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
        json.dumps(_report(results, manifest), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return _report(results, manifest)


def _report(results: list[dict], manifest=None) -> dict:
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
        "mode": manifest.to_dict().get("corpus_mode") if manifest else None,
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
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=["sample-v1", "full-v1"])
    parser.add_argument("--report-out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = main(args.mode, args.report_out)
    print(json.dumps(report, indent=2))
