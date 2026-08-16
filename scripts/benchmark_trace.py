"""Per-question Continuum trace (debug/demo).

Prints the layered path for one question:

    Question
      → retrieval candidates
      → entity resolution (mention → canonical key)
      → state resolution
      → evidence selection
      → answer

Usage:
    python scripts/benchmark_trace.py q-single-01 [--questions FILE]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.benchmark import answer
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = ROOT / "data" / "labels" / "eval-questions.jsonl"


def main(question_id: str, questions_path: Path) -> int:
    questions = [json.loads(line) for line in questions_path.open(encoding="utf-8") if line.strip()]
    question = next((q for q in questions if q.get("question_id") == question_id), None)
    if question is None:
        print(f"question {question_id!r} not found in {questions_path}")
        return 1

    with HydraDBClient() as client:
        store = EntityStore(client)
        result = answer(client, question, entity_store=store)

    print(f"QUESTION [{question_id}] ({question.get('category')})")
    print(f"  {question.get('question')}")
    print(f"  evidence_entity: {question.get('evidence_entity')}  predicate: {question.get('predicate')}")
    print()
    print("LAYERS")
    for name in ("retrieval", "entity_resolution", "state", "evidence_selection"):
        layer = result["layers"].get(name, {})
        print(f"  {name:<20} {json.dumps(layer, ensure_ascii=False)[:110]}")
    print()
    print("STATE")
    state = result["state_result"]
    print(f"  status={state.get('status')}  value={state.get('value')}")
    print(f"  conflicts={result['conflicts']}")
    print()
    print("EVIDENCE")
    for item in result["evidence"]:
        print(f"  - {item.get('source')} | {item.get('artifact_id')} | obs={item.get('observed_at')}")
    print()
    print("ANSWER:", result["answer"])
    print("TRACE")
    for step in result["trace"]:
        print(f"  {step}")
    print()
    print(f"latency: {json.dumps({k: round(v, 2) for k, v in result['latency_ms'].items()}, ensure_ascii=False)}")
    print(f"context: {json.dumps(result['context'], ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("question_id")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    args = parser.parse_args()
    raise SystemExit(main(args.question_id, args.questions))
