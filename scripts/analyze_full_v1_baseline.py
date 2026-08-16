#!/usr/bin/env python3
"""Analyze full-v1 baseline run and generate comparison + markdown report."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from continuum.eval.benchmark.baseline import run_dir
from continuum.eval.benchmark.failures import build_failure_analysis
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, SYSTEMS, git_commit_sha, load_questions, write_json
from continuum.eval.benchmark.scoring import score_answer, score_document_recall, score_rows, summarize_context, summarize_latency

ROOT = Path(__file__).resolve().parents[1]


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _category_breakdown(rows: list[dict], questions_by_id: dict[str, dict]) -> dict[str, dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        q = questions_by_id.get(str(row["question_id"]), {})
        buckets[str(q.get("question_type", "unknown"))].append(row)

    out: dict[str, dict] = {}
    for category, group in buckets.items():
        correct = sum(
            1
            for r in group
            if score_answer(str(r.get("answer", "")), str(questions_by_id[str(r["question_id"])].get("gold_answer", "")))
        )
        recalls = [
            score_document_recall(r.get("retrieved_artifacts") or [], questions_by_id[str(r["question_id"])].get("expected_doc_ids") or [])
            for r in group
        ]
        recalls = [v for v in recalls if v is not None]
        out[category] = {
            "count": len(group),
            "answer_correctness": round(correct / max(len(group), 1), 4),
            "document_recall_mean": round(statistics.mean(recalls), 4) if recalls else None,
            "latency_p50": summarize_latency(group).get("p50"),
        }
    return out


def _integrity(rows_by_system: dict[str, list[dict]], expected_questions: int) -> dict:
    total = sum(len(rows) for rows in rows_by_system.values())
    expected = expected_questions * len(rows_by_system)
    missing = {}
    for system, rows in rows_by_system.items():
        missing[system] = expected_questions - len(rows)
    return {
        "expected_results": expected,
        "actual_results": total,
        "complete": total == expected,
        "missing_by_system": missing,
    }


def _markdown(report: dict, out_path: Path) -> None:
    lines = [
        "# Benchmark v1 Analysis — full-v1-baseline-001",
        "",
        "## Executive summary",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Commit: `{report.get('commit_sha', 'unknown')}`",
        f"- Questions: {report['question_count']}",
        f"- Complete: {report['integrity']['complete']}",
        "",
        "## Official scores",
        "",
    ]
    for system, scores in report.get("official_score", {}).items():
        lines.append(f"### {system}")
        lines.append(f"- {scores}")
        lines.append("")

    if report.get("graph_coverage"):
        lines.extend([
            "## Graph coverage (Continuum)",
            "",
            f"- {report['graph_coverage']}",
            "",
            "Sparse graph coverage is expected: ~10 real claims loaded, 512K-doc corpus unchanged.",
            "",
        ])

    lines.extend(["## Context efficiency", ""])
    for system, ctx in report.get("context_efficiency", {}).items():
        lines.append(f"- **{system}**: {ctx}")

    lines.extend(["", "## Failure taxonomy", "", f"- {report.get('failure_analysis', {}).get('failure_summary', {})}", ""])
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="full-v1-baseline-001")
    parser.add_argument("--root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    args = parser.parse_args()

    out_root = run_dir(args.run_id, args.root)
    questions = load_questions("full-v1", args.root)
    questions_by_id = {str(q["question_id"]): q for q in questions}

    rows_by_system: dict[str, list[dict]] = {}
    system_reports: dict[str, dict] = {}
    for system in SYSTEMS:
        rows = _load_rows(out_root / system / "results.jsonl")
        rows_by_system[system] = rows
        if rows:
            system_reports[system] = {
                "official_score": score_rows(rows, questions_by_id),
                "context_efficiency": summarize_context(rows),
                "latency": summarize_latency(rows),
            }

    all_rows = [row for rows in rows_by_system.values() for row in rows]
    failure = build_failure_analysis(all_rows, questions_by_id)

    graph_report = None
    continuum_report_path = out_root / "continuum" / "report.json"
    if continuum_report_path.exists():
        graph_report = json.loads(continuum_report_path.read_text(encoding="utf-8")).get("graph_coverage")

    comparison = {
        "run_id": args.run_id,
        "commit_sha": git_commit_sha(),
        "generated_at": datetime.now(UTC).isoformat(),
        "question_count": len(questions),
        "official_score": {s: r["official_score"] for s, r in system_reports.items()},
        "context_efficiency": {s: r["context_efficiency"] for s, r in system_reports.items()},
        "latency": {s: r["latency"] for s, r in system_reports.items()},
        "category_breakdown": {
            system: _category_breakdown(rows, questions_by_id)
            for system, rows in rows_by_system.items()
        },
        "graph_coverage": graph_report,
        "integrity": _integrity(rows_by_system, len(questions)),
        "failure_analysis": failure,
    }
    write_json(out_root / "comparison.json", comparison)
    write_json(out_root / "full-v1-failure-analysis.json", failure)
    write_json(
        ROOT / "data" / "metadata" / "benchmark_full_v1.json",
        {
            "run_id": args.run_id,
            "commit_sha": git_commit_sha(),
            "dataset_version": "v1.0.0",
            "question_count": len(questions),
            "generated_at": datetime.now(UTC).isoformat(),
            "comparison_path": str(out_root / "comparison.json"),
        },
    )

    md_path = ROOT / "docs" / "benchmark-v1-analysis.md"
    _markdown({**comparison, "failure_analysis": failure}, md_path)
    print(json.dumps(comparison["integrity"], indent=2))


if __name__ == "__main__":
    main()
