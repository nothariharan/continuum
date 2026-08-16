"""Continuum benchmark adapter — the benchmark-facing entry point.

The runner calls:

    from continuum.benchmark import answer
    result = answer(client, question, entity_store=None, answer_generator=None)

or for a batch:

    results = answer_many(client, questions)

The result shape is the frozen contract (continuum.benchmark.contract).
"""

from __future__ import annotations

from typing import Any, Iterable

from continuum.hydradb import HydraDBClient

from .contract import validate_result
from .pipeline import AnswerGenerator, ContinuumPipeline


def answer(
    client: HydraDBClient,
    question: dict[str, Any],
    entity_store=None,
    answer_generator: AnswerGenerator | None = None,
) -> dict[str, Any]:
    """Answer one manifest question through the layered Continuum path."""
    pipeline = ContinuumPipeline(
        client=client,
        entity_store=entity_store,
        answer_generator=answer_generator,
    )
    result = pipeline.answer(question)
    validate_result(result)
    return result


def answer_many(
    client: HydraDBClient,
    questions: Iterable[dict[str, Any]],
    entity_store=None,
    answer_generator: AnswerGenerator | None = None,
) -> list[dict[str, Any]]:
    return [
        answer(client, q, entity_store=entity_store, answer_generator=answer_generator)
        for q in questions
    ]
