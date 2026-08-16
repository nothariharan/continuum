"""Hard-question regression check for the Continuum benchmark adapter.

Runs the layered Continuum pipeline over the hard regression fixture and
reports which classes pass. Used whenever entity resolution, traversal,
state, or evidence selection changes.

Usage:
    python scripts/check_benchmark_regression.py [--questions FILE]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from continuum.benchmark import answer_many
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = ROOT / "benchmark" / "regression" / "questions.jsonl"
DEFAULT_OUT = ROOT / "data" / "metadata" / "benchmark_regression_report.json"


def _expected_match(got: str, expected: str) -> bool:
    got_n = " ".join(got.lower().split())
    exp_n = " ".join(expected.lower().split())
    if got_n == exp_n:
        return True
    if exp_n == "unknown" and got_n in {"unknown", "absent"}:
        return True
    if exp_n == "conflict" and "conflict" in got_n:
        return True
    for verdict in ("same", "different", "uncertain"):
        if exp_n == verdict and got_n.startswith(verdict):
            return True
    if re.search(r"^[a-z0-9_-]{8,}", exp_n) and exp_n[:16] in got_n:
        return True
    return False


def main(questions_path: Path, report_out: Path) -> dict:
    questions = [json.loads(line) for line in questions_path.open(encoding="utf-8") if line.strip()]
    with HydraDBClient() as client:
        store = EntityStore(client)
        results = answer_many(client, questions, entity_store=store)

    rows = []
    correct = 0
    for question, result in zip(questions, results):
        ok = _expected_match(result.get("answer") or "", question.get("expected", ""))
        correct += 1 if ok else 0
        rows.append(
            {
                "question_id": question["question_id"],
                "category": question.get("category"),
                "question": question.get("question"),
                "expected": question.get("expected"),
                "got": result.get("answer"),
                "status": result.get("status"),
                "correct": ok,
                "latency_ms": round(result["latency_ms"]["total"], 2),
                "context": result["context"],
            }
        )

    from collections import Counter

    by_category = Counter(r["category"] for r in rows)
    category_correct = {cat: sum(1 for r in rows if r["category"] == cat and r["correct"]) for cat in by_category}

    report = {
        "gate": "benchmark-regression",
        "questions": len(rows),
        "correct": correct,
        "accuracy": round(correct / len(rows), 4) if rows else 0.0,
        "by_category": {cat: {"n": n, "correct": category_correct[cat]} for cat, n in by_category.items()},
        "rows": rows,
    }
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"questions: {len(rows)}  correct: {correct}  accuracy: {report['accuracy']}")
    for cat, stats in report["by_category"].items():
        print(f"  {cat:<18} {stats['correct']}/{stats['n']}")
    for row in rows:
        mark = "OK " if row["correct"] else "MISS"
        print(f"  {mark} {row['question_id']:<10} got={str(row['got'])[:35]:<37} expected={row['expected']}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    main(args.questions, args.report_out)
