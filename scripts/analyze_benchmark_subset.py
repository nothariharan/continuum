#!/usr/bin/env python3
"""Analyze subset-20pct benchmark runs and emit baseline reports."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from continuum.eval.benchmark.baseline import run_dir
from continuum.eval.benchmark.failures import build_failure_analysis, classify_row
from continuum.eval.benchmark.schema import (
    DEFAULT_BENCHMARK_ROOT,
    load_questions_from_path,
    write_json,
)
from continuum.eval.benchmark.scoring import score_answer, score_document_recall, score_rows, summarize_latency

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "benchmark-results"


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _category_breakdown(rows: list[dict], questions_by_id: dict[str, dict]) -> dict[str, dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        question = questions_by_id.get(str(row["question_id"]), {})
        buckets[str(question.get("question_type", "unknown"))].append(row)

    out: dict[str, dict] = {}
    for category, group in buckets.items():
        correct = sum(
            1
            for row in group
            if score_answer(
                str(row.get("answer", "")),
                str(questions_by_id[str(row["question_id"])].get("gold_answer", "")),
            )
        )
        recalls = [
            score_document_recall(
                row.get("retrieved_artifacts") or [],
                questions_by_id[str(row["question_id"])].get("expected_doc_ids") or [],
            )
            for row in group
        ]
        recalls = [value for value in recalls if value is not None]
        out[category] = {
            "count": len(group),
            "answer_correctness": round(correct / max(len(group), 1), 4),
            "document_recall_mean": round(statistics.mean(recalls), 4) if recalls else None,
        }
    return out


def _failure_table(rows: list[dict], questions_by_id: dict[str, dict]) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    for row in rows:
        question = questions_by_id.get(str(row["question_id"]), {})
        gold = str(question.get("gold_answer", ""))
        if score_answer(str(row.get("answer", "")), gold):
            continue
        failures.append(
            {
                "question_id": row["question_id"],
                "question_type": question.get("question_type"),
                "category": classify_row(row, question),
                "answer": row.get("answer"),
                "gold_answer": gold,
                "error": row.get("error"),
            }
        )

    counts = Counter(item["category"] for item in failures)
    total = max(len(failures), 1)
    table = []
    for category, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        examples = [item["question_id"] for item in failures if item["category"] == category][:5]
        table.append(
            {
                "failure_type": category,
                "count": count,
                "pct_of_failures": round(100 * count / total, 1),
                "example_question_ids": examples,
            }
        )
    return table


def analyze_run(
    *,
    run_id: str,
    system: str,
    questions_file: Path,
    root: Path,
    out_dir: Path,
    label: str,
) -> dict:
    subset_root = root / "subset-20pct"
    questions = load_questions_from_path(questions_file)
    questions_by_id = {str(q["question_id"]): q for q in questions}
    results_path = run_dir(run_id, root, subset=True) / system / "results.jsonl"
    rows = _load_rows(results_path)
    if not rows:
        raise FileNotFoundError(f"no results at {results_path}")

    official = score_rows(rows, questions_by_id)
    correct = sum(
        1
        for row in rows
        if score_answer(
            str(row.get("answer", "")),
            str(questions_by_id[str(row["question_id"])].get("gold_answer", "")),
        )
    )
    unanswered = sum(1 for row in rows if not str(row.get("answer", "")).strip())
    payload = {
        "label": label,
        "run_id": run_id,
        "system": system,
        "question_count": len(rows),
        "official_score": official,
        "correct": correct,
        "incorrect": len(rows) - correct - unanswered,
        "unanswered": unanswered,
        "latency": summarize_latency(rows),
        "category_breakdown": _category_breakdown(rows, questions_by_id),
        "failure_analysis": build_failure_analysis(rows, questions_by_id),
        "failure_table": _failure_table(rows, questions_by_id),
        "generated_at": datetime.now(UTC).isoformat(),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / f"{label}.json", payload)

    summary_lines = [
        f"# Benchmark subset report — {label}",
        "",
        f"- Run ID: `{run_id}`",
        f"- System: `{system}`",
        f"- Questions: {len(rows)}",
        f"- Correct: {correct}",
        f"- Incorrect: {payload['incorrect']}",
        f"- Unanswered: {unanswered}",
        f"- Answer correctness: {official.get('answer_correctness')}",
        f"- Document recall mean: {official.get('document_recall_mean')}",
        "",
        "## Category breakdown",
        "",
        "| question_type | count | answer_correctness | document_recall_mean |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category, stats in sorted(payload["category_breakdown"].items()):
        summary_lines.append(
            f"| {category} | {stats['count']} | {stats['answer_correctness']} | {stats['document_recall_mean']} |"
        )

    error_lines = [
        f"# Benchmark subset errors — {label}",
        "",
        "| Failure type | Count | % of failures | Example question_ids |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in payload["failure_table"]:
        error_lines.append(
            f"| {row['failure_type']} | {row['count']} | {row['pct_of_failures']} | {', '.join(row['example_question_ids'])} |"
        )

    (out_dir / f"{label}-summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    (out_dir / f"{label}-errors.md").write_text("\n".join(error_lines) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="subset-20pct-mock-001")
    parser.add_argument("--system", default="continuum")
    parser.add_argument(
        "--questions-file",
        type=Path,
        default=DEFAULT_BENCHMARK_ROOT / "subset-20pct" / "questions.jsonl",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--label", default="baseline-20pct")
    args = parser.parse_args()

    payload = analyze_run(
        run_id=args.run_id,
        system=args.system,
        questions_file=args.questions_file,
        root=args.root,
        out_dir=args.out_dir,
        label=args.label,
    )
    print(json.dumps({"label": payload["label"], "official_score": payload["official_score"]}, indent=2))


if __name__ == "__main__":
    main()
