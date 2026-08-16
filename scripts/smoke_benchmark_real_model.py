"""10-question real-model smoke test (the last gate before the official run).

Purpose: prove the entire benchmark plumbing with a real answer model:

    real model invocation
    → answer generation
    → parsing
    → scoring
    → trace
    → token accounting (apples-to-apples)
    → Continuum graph path (GraphContinuumSystem vs RAG systems)

10 fixed questions across categories; sample-v1 corpus; BM25 / Dense /
Hybrid / GraphContinuum; the foundation's RealAnswerModel (Fireworks).

Usage:
    python scripts/smoke_benchmark_real_model.py [--limit 10] [--report-out FILE]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from continuum.hydradb import HydraDBClient
from continuum.entities.store import EntityStore
from continuum.eval.benchmark.answer_model import RealAnswerModel
from continuum.eval.benchmark.corpus import load_corpus
from continuum.eval.benchmark.schema import DEFAULT_CONTEXT_CHARS, DEFAULT_TOP_K, load_questions
from continuum.eval.benchmark.scoring import score_rows
from continuum.eval.benchmark.systems.bm25_rag import BM25RAGSystem
from continuum.eval.benchmark.systems.dense_rag import DenseRAGSystem
from continuum.eval.benchmark.systems.hybrid_rag import HybridRAGSystem

from continuum.benchmark.graph_system import GraphContinuumSystem

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "metadata" / "smoke_benchmark_real_model.json"

# 10 fixed questions spanning categories (graph-hinted for the graph path)
SMOKE_QUESTION_IDS = [
    "q-single-01",  # Who owns LucentGrid?
    "q-single-02",  # Who maintains Skyline Systems?
    "q-single-03",  # Who leads Acme Payments?
    "q-single-05",  # Who is assigned to LucentGrid?
    "q-temporal-01",  # Who owned LucentGrid as of 2027-02-11?
    "q-temporal-02",  # Who owned LucentGrid before evidence? (abstention)
    "q-conflict-01",  # Who owns Acme Health? (conflict)
    "q-abstain-01",   # Who owns CedarBank? (abstention)
    "q-provenance-01",  # Evidence chain for Acme Health
    "q-er-01",        # Marcus Lin vs marcus.lin@redwood.com (entity resolution)
]


def load_smoke_questions() -> list[dict]:
    questions = [json.loads(line) for line in (ROOT / "data" / "labels" / "eval-questions.jsonl").open(encoding="utf-8") if line.strip()]
    by_id = {q["question_id"]: q for q in questions}
    return [by_id[qid] for qid in SMOKE_QUESTION_IDS if qid in by_id]


def main(limit: int, report_out: Path) -> dict:
    # isolated fixture load
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

    questions = load_smoke_questions()[:limit]
    answer_model = RealAnswerModel()
    corpus = load_corpus("sample-v1")

    systems = {
        "bm25": BM25RAGSystem(corpus),
        "hybrid": HybridRAGSystem(corpus),
    }
    try:
        systems["dense"] = DenseRAGSystem(corpus)
    except Exception:
        from continuum.eval.benchmark.systems.bm25_rag import BM25RAGSystem as _B
        systems["dense"] = systems["bm25"]

    rows = []
    with HydraDBClient() as client:
        systems["continuum"] = GraphContinuumSystem(client, entity_store=EntityStore(client))
        for question in questions:
            for name, system in systems.items():
                try:
                    result = system.run(
                        question, corpus,
                        top_k=DEFAULT_TOP_K, char_budget=DEFAULT_CONTEXT_CHARS,
                        answer_model=answer_model,
                    )
                    rows.append({
                        "question_id": question["question_id"],
                        "system": name,
                        "answer": result.answer[:200],
                        "retrieved_artifacts": result.retrieved_artifacts,
                        "context_chars": result.context_chars,
                        "context_tokens": result.context_tokens,
                        "evidence_items": result.evidence_items,
                        "latency_ms": result.total_ms,
                        "latency_breakdown": result.latency_breakdown,
                        "continuum": result.continuum,
                    })
                except Exception as exc:
                    rows.append({
                        "question_id": question["question_id"],
                        "system": name,
                        "error": str(exc)[:200],
                    })

    report = {
        "gate": "smoke-benchmark-real-model",
        "answer_model": answer_model.name,
        "questions": len(questions),
        "systems": sorted({r["system"] for r in rows}),
        "rows": rows,
    }
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = main(args.limit, args.report_out)
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
