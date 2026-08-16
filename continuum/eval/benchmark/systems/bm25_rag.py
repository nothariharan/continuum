"""BM25 RAG baseline."""

from __future__ import annotations

import time
from typing import Any

from continuum.embed.bm25 import BM25Retriever

from ..context import build_context
from ..corpus import BenchmarkCorpus
from .base import AnswerModel, SystemRunResult


class BM25RAGSystem:
    name = "bm25"

    def __init__(self, corpus: BenchmarkCorpus) -> None:
        self._corpus = corpus
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
        started = time.perf_counter()
        hits = self._retriever.search(str(question["question"]), top_k=top_k)
        retrieval_ms = (time.perf_counter() - started) * 1000
        records = [corpus.records[index] for index, _ in hits]
        context, artifact_ids, context_chars, context_tokens = build_context(records, char_budget=char_budget)
        answer, token_count, generation_ms = answer_model.generate(str(question["question"]), context)
        return SystemRunResult(
            answer=answer,
            retrieved_artifacts=artifact_ids,
            context_chars=context_chars,
            context_tokens=context_tokens,
            evidence_items=len(artifact_ids),
            latency_breakdown={
                "retrieval_ms": round(retrieval_ms, 2),
                "entity_ms": 0.0,
                "graph_ms": 0.0,
                "state_ms": 0.0,
                "generation_ms": round(generation_ms, 2),
            },
        )
