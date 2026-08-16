"""Continuum-specific diagnostic overlay (separate from official score)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIAGNOSTIC_QUESTIONS = ROOT / "data" / "labels" / "eval-questions.jsonl"


def load_diagnostic_questions(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or DEFAULT_DIAGNOSTIC_QUESTIONS
    rows: list[dict[str, Any]] = []
    with target.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_answer(answer: str) -> str:
    return " ".join((answer or "").lower().split())


def check_diagnostic_answer(got: str, expected: str) -> bool:
    got_n = normalize_answer(got)
    exp_n = normalize_answer(expected)
    if got_n == exp_n:
        return True
    if "abstain" in exp_n and "abstain" in got_n:
        return True
    if "conflict" in exp_n and "conflict" in got_n:
        return True
    for verdict in ("same", "different", "uncertain"):
        if got_n.startswith(verdict) and verdict in exp_n:
            return True
    return False


def empty_diagnostics() -> dict[str, Any]:
    return {
        "entity_resolution_correctness": None,
        "temporal_correctness": None,
        "conflict_correctness": None,
        "abstention_correctness": None,
        "provenance_correctness": None,
        "note": "Continuum diagnostics require structured eval-questions harness; not run in generic ER-Bench pass.",
    }
