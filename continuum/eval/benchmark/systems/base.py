"""Shared system adapter types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..corpus import BenchmarkCorpus


@dataclass
class SystemRunResult:
    answer: str
    retrieved_artifacts: list[str]
    context_chars: int
    context_tokens: int
    evidence_items: int
    latency_breakdown: dict[str, float] = field(default_factory=dict)
    continuum: dict[str, Any] = field(default_factory=dict)

    @property
    def total_ms(self) -> float:
        return round(sum(self.latency_breakdown.values()), 2)


class AnswerModel(Protocol):
    name: str

    def generate(self, question: str, context: str) -> tuple[str, int, float]: ...


class SystemAdapter(Protocol):
    name: str

    def run(self, question: dict[str, Any], corpus: BenchmarkCorpus, *, top_k: int, char_budget: int, answer_model: AnswerModel) -> SystemRunResult: ...
