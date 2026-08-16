"""Graph-backed Continuum benchmark system — the real Continuum adapter.

Implements the benchmark foundation's SystemAdapter protocol
(continuum.eval.benchmark.systems.base) using the layered graph pipeline
(continuum.benchmark.answer). This is the drop-in replacement for the
harness's retrieval-only ContinuumSystem when graph state is available:

    question
      → continuum.benchmark.answer (layered: retrieval, entity resolution,
        state, conflicts, evidence, answer generation)
      → SystemRunResult (the benchmark's envelope)

The answer model seam stays the benchmark's: the pipeline produces the
structured context, the harness's answer_model generates the final text.
"""

from __future__ import annotations

import time
from typing import Any

from continuum.benchmark import answer as continuum_answer
from continuum.hydradb import HydraDBClient

try:
    from continuum.eval.benchmark.context import estimate_tokens
    from continuum.eval.benchmark.systems.base import AnswerModel, SystemRunResult
    from continuum.eval.benchmark.corpus import BenchmarkCorpus
except ImportError:  # benchmark foundation not installed (defensive)
    AnswerModel = Any
    SystemRunResult = Any
    BenchmarkCorpus = Any

    def estimate_tokens(text: str) -> int:
        return max(len(text.split()), 1)


class GraphContinuumSystem:
    """Continuum with real graph state (entity resolution → HydraDB → state)."""

    name = "continuum-graph"

    def __init__(self, client: HydraDBClient, entity_store=None) -> None:
        self._client = client
        self._store = entity_store

    def run(
        self,
        question: dict[str, Any],
        corpus: BenchmarkCorpus,
        *,
        top_k: int = 5,
        char_budget: int = 12000,
        answer_model: AnswerModel | None = None,
    ) -> SystemRunResult:
        started = time.perf_counter()
        result = continuum_answer(self._client, question, entity_store=self._store)
        total_ms = (time.perf_counter() - started) * 1000

        latency = dict(result.get("latency_ms", {}))
        latency["total_ms"] = round(total_ms, 2)

        # Build the structured context the answer model will read: the state
        # envelope + evidence chain (this is the Continuum context advantage).
        state = result.get("state_result") or {}
        evidence = result.get("evidence") or []
        evidence_lines = "\n".join(
            f"- source={e.get('source')} artifact={e.get('artifact_id')} "
            f"observed={e.get('observed_at')}"
            for e in evidence
        )
        structured = (
            f"Resolved entities: {result.get('resolved_entities') or ['none']}\n"
            f"State: {state}\n"
            f"Conflicts: {result.get('conflicts') or ['none']}\n"
            f"Claims used: {result.get('claims_used') or ['none']}\n"
            f"Evidence:\n{evidence_lines or 'none'}"
        )

        # Context accounting is apples-to-apples with the RAG systems: the
        # foundation's estimate_tokens() over the CONTEXT string (not the
        # answer). The answer model returns only the final answer text.
        context_chars = min(len(structured), char_budget)
        context_tokens = estimate_tokens(structured[:char_budget])

        if answer_model is not None:
            answer, _answer_tokens, generation_ms = answer_model.generate(
                str(question.get("question", "")), structured[:char_budget]
            )
            latency["generation_ms"] = round(generation_ms, 2)
        else:
            answer = result.get("answer") or "unknown"

        return SystemRunResult(
            answer=answer,
            retrieved_artifacts=result.get("retrieval_artifacts", result.get("resolved_entities", [])),
            context_chars=context_chars,
            context_tokens=context_tokens,
            evidence_items=result.get("context", {}).get("evidence_items", 0),
            latency_breakdown=latency,
            continuum={
                "resolved_entities": result.get("resolved_entities", []),
                "claims_used": result.get("claims_used", []),
                "state_result": state,
                "conflicts": result.get("conflicts", []),
                "evidence": evidence,
            },
        )
