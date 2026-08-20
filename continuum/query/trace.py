"""Safe observability trace for a single query (Section 20).

Produces a redacted, structured view of how a question became an answer:

    question -> decomposition -> entity resolution -> state retrieval
             -> evidence sources -> answer generation

Safety: the trace carries only identifiers and resolved values — canonical
entity keys, claim/artifact ids, source names, dates. It NEVER includes access
tokens or raw private message content, so it is safe for production logs.
"""

from __future__ import annotations

from typing import Any

from continuum.hydradb import HydraDBClient
from continuum.query.decompose import decompose_question


def _evidence_refs(evidence: list[dict[str, Any]]) -> list[str]:
    """Compact 'source:artifact_id' refs — no content, no tokens."""
    refs: list[str] = []
    for item in evidence:
        source = str(item.get("source") or item.get("source_id") or "unknown").lower()
        artifact = str(item.get("artifact_id") or item.get("claim_id") or "?")
        refs.append(f"{source}:{artifact}")
    return refs


def build_query_trace(
    client: HydraDBClient,
    question: dict[str, Any],
    *,
    entity_store: Any | None = None,
) -> dict[str, Any]:
    """Return a redacted debug trace for one question.

    Runs the real answer pipeline and reports each stage's structured output.
    """
    from continuum.benchmark import answer

    ctx = decompose_question(question)
    result = answer(client, question, entity_store=entity_store)

    state = result.get("state_result") or {}
    evidence = result.get("evidence") or []
    value = state.get("value") or {}
    sources = sorted({str(e.get("source")) for e in evidence if e.get("source")})

    return {
        "question": question.get("question"),
        "decomposition": {
            "intent": ctx.intent,
            "entities": [e.mention for e in ctx.entities],
            "predicates": ctx.graph_predicates() or ([question.get("predicate")] if question.get("predicate") else []),
            "temporal": [t.kind for t in ctx.temporal],
        },
        "entity_resolution": {
            "resolved": result.get("resolved_entities") or [],
            "evidence_entity": question.get("evidence_entity"),
        },
        "state": {
            "status": state.get("status"),
            "owner": value.get("name"),
            "owner_key": value.get("entity_id"),
        },
        "evidence": {
            "sources": sources,
            "refs": _evidence_refs(evidence),
            "count": len(evidence),
            "multi_source": len(sources) > 1,
        },
        "temporal": {
            "valid_from": state.get("valid_from"),
            "valid_to": state.get("valid_to"),
            "as_of": state.get("as_of"),
        },
        "answer": {
            "status": state.get("status"),
            "value": value.get("name"),
        },
    }


def render_trace(trace: dict[str, Any]) -> str:
    """Human-readable one-block rendering of a trace (for CLI/logs)."""
    d = trace["decomposition"]
    lines = [
        f"question: {trace['question']}",
        f"  decomposition: intent={d['intent']} entities={d['entities']} predicates={d['predicates']}",
        f"  entities: {trace['entity_resolution']['resolved'] or trace['entity_resolution']['evidence_entity']}",
        f"  state: owner={trace['state']['owner']} status={trace['state']['status']}",
        f"  evidence: sources={trace['evidence']['sources']} refs={trace['evidence']['refs']}",
        f"  temporal: effective={trace['temporal']['valid_from']}",
        f"  answer: {trace['answer']['value']} ({trace['answer']['status']})",
    ]
    return "\n".join(lines)


__all__ = ["build_query_trace", "render_trace"]
