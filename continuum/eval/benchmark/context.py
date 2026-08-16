"""Context assembly and token estimation."""

from __future__ import annotations

from .corpus import BenchmarkCorpus, CorpusRecord


def estimate_tokens(text: str) -> int:
    return max(len(text.split()), 1)


def build_context(
    records: list[CorpusRecord],
    *,
    char_budget: int,
) -> tuple[str, list[str], int, int]:
    chunks: list[str] = []
    artifact_ids: list[str] = []
    used = 0
    for record in records:
        block = f"[{record.artifact_id}] {record.title}\n{record.content}\n"
        if used + len(block) > char_budget and chunks:
            break
        chunks.append(block)
        artifact_ids.append(record.artifact_id)
        used += len(block)
    context = "\n".join(chunks)
    return context, artifact_ids, len(context), estimate_tokens(context)
