"""Continuum benchmark contract — the frozen answer envelope.

The benchmark runner calls exactly one function:

    from continuum.benchmark import answer
    result = answer(question)          # question is a dict (manifest row)

and gets a structured result with this exact shape. The runner never needs
to understand HydraDB internals; Continuum exposes the layers it used so
failures can be attributed to a specific stage.

Contract (frozen for the benchmark phase):

    {
      "question_id": str,
      "question": str,
      "status": "definitive" | "absent" | "conflict" | "error",
      "answer": str | None,              # structured answer (model-agnostic)
      "resolved_entities": [str],        # canonical keys
      "claims_used": [str],              # claim ids consulted
      "state_result": {...},             # canonical state envelope
      "conflicts": [...],                # conflict subjects / claims
      "evidence": [...],                 # evidence chain items
      "layers": {
        "retrieval": {...},              # candidate artifacts/claims
        "entity_resolution": {...},      # mention -> canonical key
        "traversal": {...},              # HydraDB hops
        "state": {...},                  # state resolution outcome
        "evidence_selection": {...},     # evidence chosen
      },
      "context": {                       # context efficiency (Continuum side)
        "artifacts": int,
        "characters": int,
        "tokens_estimate": int,
        "claims": int,
        "evidence_items": int,
      },
      "latency_ms": {
        "retrieval": float,
        "entity_resolution": float,
        "traversal": float,
        "state": float,
        "evidence_selection": float,
        "total": float,
      },
      "diagnostics": {                   # Continuum-specific (never official score)
        "entity_resolution_ok": bool | None,
        "temporal_ok": bool | None,
        "conflict_ok": bool | None,
        "abstention_ok": bool | None,
        "provenance_ok": bool | None,
      },
      "trace": [...]                     # human-readable trace steps
    }
"""

from __future__ import annotations

from typing import Any

CONTRACT_FIELDS = (
    "question_id",
    "question",
    "status",
    "answer",
    "resolved_entities",
    "claims_used",
    "state_result",
    "conflicts",
    "evidence",
    "layers",
    "context",
    "latency_ms",
    "diagnostics",
    "trace",
)

LAYER_NAMES = (
    "retrieval",
    "entity_resolution",
    "traversal",
    "state",
    "evidence_selection",
)


def empty_result(question_id: str, question: str) -> dict[str, Any]:
    """A fully-shaped empty result (all keys present, safe defaults)."""
    return {
        "question_id": question_id,
        "question": question,
        "status": "absent",
        "answer": None,
        "resolved_entities": [],
        "claims_used": [],
        "state_result": {},
        "conflicts": [],
        "evidence": [],
        "layers": {name: {} for name in LAYER_NAMES},
        "context": {
            "artifacts": 0,
            "characters": 0,
            "tokens_estimate": 0,
            "claims": 0,
            "evidence_items": 0,
        },
        "latency_ms": {name: 0.0 for name in LAYER_NAMES} | {"total": 0.0},
        "diagnostics": {
            "entity_resolution_ok": None,
            "temporal_ok": None,
            "conflict_ok": None,
            "abstention_ok": None,
            "provenance_ok": None,
        },
        "trace": [],
    }


def validate_result(result: dict[str, Any]) -> None:
    """Raise if a result violates the frozen contract."""
    missing = [f for f in CONTRACT_FIELDS if f not in result]
    if missing:
        raise ValueError(f"result missing contract fields: {missing}")
    if not isinstance(result["latency_ms"], dict):
        raise ValueError("latency_ms must be a dict")
    if "total" not in result["latency_ms"]:
        raise ValueError("latency_ms must include total")
    for name in LAYER_NAMES:
        if name not in result["layers"]:
            raise ValueError(f"layers must include {name}")
