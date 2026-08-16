"""Deterministic mock answer generator for benchmark plumbing."""

from __future__ import annotations

from dataclasses import dataclass

ANSWER_PROMPT = (
    "Answer the question using only the provided context. "
    "If the context is insufficient, respond with 'unknown - abstain'.\n\n"
    "Question: {question}\n\nContext:\n{context}\n\nAnswer:"
)


@dataclass
class MockAnswerModel:
    name: str = "mock-v1"

    def generate(self, question: str, context: str) -> tuple[str, int, float]:
        first_line = ""
        for line in context.splitlines():
            if line.strip():
                first_line = line.strip()
                break
        if not first_line:
            return "unknown - abstain", 0, 0.0
        answer = f"mock: {first_line[:120]}"
        return answer, estimate_tokens(answer), 0.0


def estimate_tokens(text: str) -> int:
    return max(len(text.split()), 1)


def format_prompt(question: str, context: str) -> str:
    return ANSWER_PROMPT.format(question=question, context=context)
