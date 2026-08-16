"""Benchmark foundation runner."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .answer_mock import MockAnswerModel
from .answer_model import RealAnswerModel
from .corpus import load_corpus
from .diagnostics import empty_diagnostics
from .schema import (
    DEFAULT_BENCHMARK_ROOT,
    SYSTEMS,
    BenchmarkManifest,
    load_manifest,
    load_questions,
    mode_root,
    write_json,
)
from .scoring import (
    aggregate_context_efficiency,
    aggregate_latency,
    aggregate_official_scores,
    score_rows,
    summarize_context,
    summarize_latency,
    summarize_stage_latency,
)
from .systems.bm25_rag import BM25RAGSystem
from .systems.continuum import ContinuumSystem
from .systems.dense_rag import DenseRAGSystem
from .systems.hybrid_rag import HybridRAGSystem


def _answer_model(manifest: BenchmarkManifest, answer_model: str):
    if answer_model == "real":
        return RealAnswerModel(
            temperature=manifest.answer_temperature,
            timeout_s=manifest.answer_timeout_s,
        )
    return MockAnswerModel(name=manifest.answer_model)


def _build_systems(
    corpus,
    *,
    with_graph: bool,
    fail_on_fallback: bool = False,
    graph_client=None,
    entity_store=None,
) -> dict[str, Any]:
    bm25 = BM25RAGSystem(corpus)
    systems: dict[str, Any] = {"bm25": bm25}

    class _FallbackAdapter:
        def __init__(self, name: str, inner: BM25RAGSystem) -> None:
            self.name = name
            self._inner = inner

        def run(self, question, corpus, *, top_k, char_budget, answer_model):
            return self._inner.run(
                question,
                corpus,
                top_k=top_k,
                char_budget=char_budget,
                answer_model=answer_model,
            )

    try:
        systems["dense"] = DenseRAGSystem(corpus)
        systems["hybrid"] = HybridRAGSystem(corpus)
    except Exception as exc:
        if fail_on_fallback:
            raise RuntimeError(f"dense/hybrid initialization failed: {exc}") from exc
        systems["dense"] = _FallbackAdapter("dense", bm25)
        systems["hybrid"] = _FallbackAdapter("hybrid", bm25)

    if with_graph:
        if graph_client is None:
            raise RuntimeError("with_graph requires an active HydraDB client")
        from continuum.benchmark.graph_system import GraphContinuumSystem

        systems["continuum"] = GraphContinuumSystem(graph_client, entity_store=entity_store)
    else:
        systems["continuum"] = ContinuumSystem(corpus, with_graph=False)
    return systems


def _build_single_system(
    corpus,
    system_name: str,
    *,
    with_graph: bool,
    fail_on_fallback: bool = False,
    graph_client=None,
    entity_store=None,
):
    if system_name == "bm25":
        return BM25RAGSystem(corpus)
    if system_name == "dense":
        try:
            return DenseRAGSystem(corpus)
        except Exception as exc:
            if fail_on_fallback:
                raise RuntimeError(f"dense initialization failed: {exc}") from exc
            return BM25RAGSystem(corpus)
    if system_name == "hybrid":
        try:
            return HybridRAGSystem(corpus)
        except Exception as exc:
            if fail_on_fallback:
                raise RuntimeError(f"hybrid initialization failed: {exc}") from exc
            return BM25RAGSystem(corpus)
    if system_name == "continuum":
        if with_graph:
            if graph_client is None:
                raise RuntimeError("with_graph requires an active HydraDB client")
            from continuum.benchmark.graph_system import GraphContinuumSystem

            return GraphContinuumSystem(graph_client, entity_store=entity_store)
        return ContinuumSystem(corpus, with_graph=False)
    raise ValueError(f"unknown system: {system_name}")


def _result_row(question_id: str, system: str, model_name: str, run_result) -> dict[str, Any]:
    row = {
        "question_id": question_id,
        "system": system,
        "answer": run_result.answer,
        "retrieved_artifacts": run_result.retrieved_artifacts,
        "model": model_name,
        "latency_ms": run_result.total_ms,
        "latency_breakdown": run_result.latency_breakdown,
        "token_count": max(len(run_result.answer.split()), 1),
        "context_chars": run_result.context_chars,
        "context_tokens": run_result.context_tokens,
        "evidence_items": run_result.evidence_items,
    }
    if run_result.continuum:
        row.update(
            {
                "resolved_entities": run_result.continuum.get("resolved_entities", []),
                "claims_used": run_result.continuum.get("claims_used", []),
                "state_result": run_result.continuum.get("state_result", {}),
                "conflicts": run_result.continuum.get("conflicts", []),
                "evidence": run_result.continuum.get("evidence", []),
            }
        )
    return row


def run_benchmark(
    mode: str,
    *,
    answer_model: str = "mock",
    with_graph: bool = False,
    root: Path | None = None,
    regression: bool = False,
    corpus_limit: int = 0,
) -> dict[str, Any]:
    benchmark_root = root or DEFAULT_BENCHMARK_ROOT
    manifest = load_manifest(mode, benchmark_root)
    questions = load_questions(mode, benchmark_root, regression=regression)
    corpus = load_corpus(mode, corpus_limit=corpus_limit)
    model = _answer_model(manifest, answer_model)
    systems = _build_systems(corpus, with_graph=with_graph)
    questions_by_id = {str(q["question_id"]): q for q in questions}

    system_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in SYSTEMS}
    started = time.perf_counter()
    for question in questions:
        for system_name, adapter in systems.items():
            result = adapter.run(
                question,
                corpus,
                top_k=manifest.top_k,
                char_budget=manifest.context_char_budget,
                answer_model=model,
            )
            system_rows[system_name].append(
                _result_row(str(question["question_id"]), system_name, model.name, result)
            )

    reports_dir = benchmark_root / "reports" / mode
    reports_dir.mkdir(parents=True, exist_ok=True)
    system_reports: dict[str, dict[str, Any]] = {}
    for system_name, rows in system_rows.items():
        report = {
            "system": system_name,
            "corpus_mode": mode,
            "official_benchmark": manifest.official_benchmark,
            "official_score": score_rows(rows, questions_by_id),
            "latency": {
                "total": summarize_latency(rows),
                "stages": summarize_stage_latency(rows),
            },
            "context_efficiency": summarize_context(rows),
            "rows": rows,
        }
        system_reports[system_name] = report
        write_json(reports_dir / f"{system_name}.json", report)

    comparison = {
        "benchmark_version": manifest.benchmark_version,
        "corpus_mode": mode,
        "official_benchmark": manifest.official_benchmark,
        "question_count": len(questions),
        "answer_model": model.name,
        "runtime_ms": round((time.perf_counter() - started) * 1000, 2),
        "official_score": aggregate_official_scores(system_reports),
        "continuum_diagnostics": empty_diagnostics(),
        "latency": aggregate_latency(system_reports),
        "context_efficiency": aggregate_context_efficiency(system_reports),
    }
    write_json(reports_dir / "comparison.json", comparison)
    return comparison


def trace_question(
    question_id: str,
    *,
    mode: str = "sample-v1",
    answer_model: str = "mock",
    with_graph: bool = False,
    root: Path | None = None,
) -> str:
    benchmark_root = root or DEFAULT_BENCHMARK_ROOT
    manifest = load_manifest(mode, benchmark_root)
    questions = load_questions(mode, benchmark_root)
    question = next((q for q in questions if q["question_id"] == question_id), None)
    if question is None:
        raise SystemExit(f"question_id not found in {mode}: {question_id}")

    corpus = load_corpus(mode)
    model = _answer_model(manifest, answer_model)
    systems = _build_systems(corpus, with_graph=with_graph)

    lines = [f"Question: {question['question']}", f"question_id: {question_id}", ""]
    for system_name, adapter in systems.items():
        result = adapter.run(
            question,
            corpus,
            top_k=manifest.top_k,
            char_budget=manifest.context_char_budget,
            answer_model=model,
        )
        lines.append(system_name.upper() + ":")
        lines.append(f"  retrieved: {result.retrieved_artifacts}")
        lines.append(f"  context_chars: {result.context_chars}")
        lines.append(f"  answer: {result.answer}")
        if result.continuum:
            lines.append(f"  resolved_entities: {result.continuum.get('resolved_entities')}")
            lines.append(f"  state_result: {result.continuum.get('state_result')}")
            lines.append(f"  evidence: {result.continuum.get('evidence')}")
        lines.append(f"  latency_ms: {result.total_ms}")
        lines.append("")
    return "\n".join(lines)
