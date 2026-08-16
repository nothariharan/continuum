"""Continuum path: retrieval + structured state context (graph optional)."""

from __future__ import annotations

import time
from typing import Any

from continuum.embed.bm25 import BM25Retriever
from continuum.embed.retrieval import HybridRetriever
from continuum.embed.sentence_transformer import SentenceTransformerProvider

from ..context import build_context
from ..corpus import BenchmarkCorpus
from .base import AnswerModel, SystemRunResult


class ContinuumSystem:
    name = "continuum"

    def __init__(self, corpus: BenchmarkCorpus, *, with_graph: bool = False) -> None:
        self._corpus = corpus
        self._with_graph = with_graph
        self._retriever = None
        try:
            provider = SentenceTransformerProvider(model_name="all-MiniLM-L6-v2")
            self._retriever = HybridRetriever(provider, corpus.texts)
        except Exception:
            self._retriever = BM25Retriever(corpus.texts)

    def run(
        self,
        question: dict[str, Any],
        corpus: BenchmarkCorpus,
        *,
        top_k: int,
        char_budget: int,
        answer_model: AnswerModel,
    ) -> SystemRunResult:
        entity_ms = 0.0
        graph_ms = 0.0
        state_ms = 0.0
        resolved_entities: list[str] = []
        claims_used: list[str] = []
        conflicts: list[str] = []
        evidence: list[dict[str, Any]] = []
        state_result: dict[str, Any] = {"status": "absent"}

        started = time.perf_counter()
        hits = self._retriever.search(str(question["question"]), top_k=top_k)
        retrieval_ms = (time.perf_counter() - started) * 1000

        records = [corpus.records[index] for index, _ in hits]
        retrieval_context, artifact_ids, context_chars, context_tokens = build_context(
            records, char_budget=max(char_budget // 2, 1000)
        )

        if self._with_graph:
            entity_started = time.perf_counter()
            entity_ms = (time.perf_counter() - entity_started) * 1000
            graph_started = time.perf_counter()
            graph_ms = (time.perf_counter() - graph_started) * 1000
            state_started = time.perf_counter()
            state_result = {"status": "stub", "note": "graph fixture path reserved for --with-graph integration"}
            state_ms = (time.perf_counter() - state_started) * 1000

        structured = (
            f"Resolved entities: {resolved_entities or ['none']}\n"
            f"State: {state_result}\n"
            f"Conflicts: {conflicts or ['none']}\n"
            f"Evidence items: {len(evidence)}\n"
            f"Retrieved context:\n{retrieval_context}"
        )
        remaining = max(char_budget - len(structured), 0)
        if remaining < len(retrieval_context):
            structured = structured[:char_budget]

        answer, token_count, generation_ms = answer_model.generate(str(question["question"]), structured)
        return SystemRunResult(
            answer=answer,
            retrieved_artifacts=artifact_ids,
            context_chars=min(len(structured), char_budget),
            context_tokens=max(len(structured.split()), 1),
            evidence_items=len(evidence) or len(artifact_ids),
            latency_breakdown={
                "retrieval_ms": round(retrieval_ms, 2),
                "entity_ms": round(entity_ms, 2),
                "graph_ms": round(graph_ms, 2),
                "state_ms": round(state_ms, 2),
                "generation_ms": round(generation_ms, 2),
            },
            continuum={
                "resolved_entities": resolved_entities,
                "claims_used": claims_used,
                "state_result": state_result,
                "conflicts": conflicts,
                "evidence": evidence,
            },
        )
