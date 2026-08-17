"""Full-v1 baseline orchestration — frozen run IDs, raw JSONL, resume."""

from __future__ import annotations

import json
import platform
import resource
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient

from .corpus import load_corpus
from .runner import _answer_model, _build_single_system, _build_systems, _result_row
from .schema import (
    DEFAULT_BENCHMARK_ROOT,
    BenchmarkManifest,
    git_commit_sha,
    load_manifest,
    load_questions,
    validate_result_row,
    write_json,
)
from .scoring import score_rows, summarize_context, summarize_latency, summarize_stage_latency


def _environment_metadata() -> dict[str, Any]:
    import numpy
    import scipy

    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
    }


def run_dir(run_id: str, root: Path | None = None) -> Path:
    return (root or DEFAULT_BENCHMARK_ROOT) / "full-v1" / "runs" / run_id


def _load_completed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            done.add(str(row["question_id"]))
    return done


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        import os

        os.fsync(handle.fileno())


def _graph_coverage(row: dict[str, Any]) -> dict[str, Any]:
    state = row.get("state_result") or {}
    status = state.get("status") if isinstance(state, dict) else None
    claims = row.get("claims_used") or []
    entities = row.get("resolved_entities") or []
    graph_state_hit = status not in (None, "absent", "stub") and bool(
        state.get("value") or state.get("names") or state.get("evidence") or claims
    )
    return {
        "graph_state_hit": graph_state_hit,
        "claims_used_count": len(claims),
        "entity_resolved_count": len(entities),
        "graph_abstain": status == "absent" or not graph_state_hit,
    }


def run_baseline(
    *,
    mode: str = "full-v1",
    run_id: str,
    answer_model: str = "real",
    with_graph: bool = True,
    system: str | None = None,
    regression: bool = False,
    corpus_limit: int = 0,
    fail_on_fallback: bool = True,
    index_only: bool = False,
    max_questions: int = 0,
    root: Path | None = None,
    graph_client: HydraDBClient | None = None,
    entity_store: EntityStore | None = None,
) -> dict[str, Any]:
    benchmark_root = root or DEFAULT_BENCHMARK_ROOT
    manifest = load_manifest(mode, benchmark_root)
    questions = load_questions(mode, benchmark_root, regression=regression)
    if max_questions > 0:
        questions = questions[:max_questions]
    out_root = run_dir(run_id, benchmark_root)

    corpus_started = time.perf_counter()
    corpus = load_corpus(mode, corpus_limit=corpus_limit)
    corpus_load_s = round(time.perf_counter() - corpus_started, 2)

    if index_only:
        target = system or "bm25"
        _build_single_system(
            corpus,
            target,
            with_graph=with_graph,
            fail_on_fallback=fail_on_fallback,
            graph_client=graph_client,
            entity_store=entity_store,
        )
        return {
            "run_id": run_id,
            "index_only": True,
            "system": target,
            "corpus_records": len(corpus.records),
            "corpus_load_s": corpus_load_s,
            "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 2),
        }

    model = _answer_model(manifest, answer_model)
    if system and system != "all":
        systems = {
            system: _build_single_system(
                corpus,
                system,
                with_graph=with_graph,
                fail_on_fallback=fail_on_fallback,
                graph_client=graph_client,
                entity_store=entity_store,
            )
        }
    else:
        systems = _build_systems(
            corpus,
            with_graph=with_graph,
            fail_on_fallback=fail_on_fallback,
            graph_client=graph_client,
            entity_store=entity_store,
        )

    questions_by_id = {str(q["question_id"]): q for q in questions}
    run_manifest_path = out_root / "run_manifest.json"
    if not run_manifest_path.exists():
        write_json(
            run_manifest_path,
            {
                "run_id": run_id,
                "mode": mode,
                "regression": regression,
                "answer_model": model.name,
                "with_graph": with_graph,
                "commit_sha": git_commit_sha(),
                "corpus_records_loaded": len(corpus.records),
                "corpus_limit": corpus_limit,
                "question_count": len(questions),
                "started_at": datetime.now(UTC).isoformat(),
                "environment": _environment_metadata(),
                "top_k": manifest.top_k,
                "context_char_budget": manifest.context_char_budget,
                "temperature": manifest.answer_temperature,
                "timeout_s": manifest.answer_timeout_s,
            },
        )

    started = time.perf_counter()

    for question in questions:
        qid = str(question["question_id"])
        for system_name, adapter in systems.items():
            results_path = out_root / system_name / "results.jsonl"
            if qid in _load_completed_ids(results_path):
                continue

            row_started = datetime.now(UTC).isoformat()
            try:
                result = adapter.run(
                    question,
                    corpus,
                    top_k=manifest.top_k,
                    char_budget=manifest.context_char_budget,
                    answer_model=model,
                )
                row = _result_row(qid, system_name, model.name, result)
                row["timestamp"] = row_started
                row["model_config"] = {
                    "temperature": manifest.answer_temperature,
                    "timeout_s": manifest.answer_timeout_s,
                    "top_k": manifest.top_k,
                    "context_char_budget": manifest.context_char_budget,
                }
                row["error"] = None
                if system_name == "continuum":
                    row["graph_coverage"] = _graph_coverage(row)
            except Exception as exc:
                row = {
                    "question_id": qid,
                    "system": system_name,
                    "answer": "",
                    "retrieved_artifacts": [],
                    "model": model.name,
                    "latency_ms": 0,
                    "latency_breakdown": {},
                    "context_chars": 0,
                    "context_tokens": 0,
                    "evidence_items": 0,
                    "timestamp": row_started,
                    "model_config": {},
                    "error": str(exc),
                }
            errors = validate_result_row(row)
            if errors and row.get("error") is None:
                row["error"] = "; ".join(errors)
            _append_jsonl(results_path, row)

    for system_name in systems:
        results_path = out_root / system_name / "results.jsonl"
        rows = [
            json.loads(line)
            for line in results_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] if results_path.exists() else []
        report = {
            "run_id": run_id,
            "system": system_name,
            "corpus_mode": mode,
            "official_benchmark": manifest.official_benchmark,
            "official_score": score_rows(rows, questions_by_id),
            "latency": {
                "total": summarize_latency(rows),
                "stages": summarize_stage_latency(rows),
            },
            "context_efficiency": summarize_context(rows),
            "row_count": len(rows),
        }
        if system_name == "continuum":
            coverage_rows = [r.get("graph_coverage", {}) for r in rows if r.get("graph_coverage")]
            if coverage_rows:
                hits = sum(1 for c in coverage_rows if c.get("graph_state_hit"))
                report["graph_coverage"] = {
                    "graph_state_hit_rate": round(hits / len(coverage_rows), 4),
                    "graph_abstain_rate": round(
                        sum(1 for c in coverage_rows if c.get("graph_abstain")) / len(coverage_rows),
                        4,
                    ),
                    "mean_claims_used": round(
                        sum(c.get("claims_used_count", 0) for c in coverage_rows) / len(coverage_rows),
                        4,
                    ),
                }
        write_json(out_root / system_name / "report.json", report)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    summary = {
        "run_id": run_id,
        "systems": list(systems.keys()),
        "questions": len(questions),
        "runtime_ms": elapsed_ms,
        "output_dir": str(out_root),
    }
    write_json(out_root / "run_summary.json", summary)
    return summary


def ensure_graph_fixture() -> tuple[HydraDBClient, EntityStore]:
    """Load HydraDB sample artifacts + real claims (no expansion)."""
    import subprocess

    root = Path(__file__).resolve().parents[3]
    subprocess.run(
        [sys.executable, str(root / "scripts" / "dataset_load_hydradb.py"), "--reset"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "load_phase2b_claims.py"),
            "--reset",
            "--real",
            "--claims",
            str(root / "data" / "fixtures" / "phase2b_real_claims.jsonl"),
            "--resolutions",
            str(root / "data" / "fixtures" / "phase2b" / "resolutions-real.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    client = HydraDBClient()
    client.health_check()
    return client, EntityStore(client)
