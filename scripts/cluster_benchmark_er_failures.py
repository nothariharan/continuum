#!/usr/bin/env python3
"""Trace-based failure clustering for subset-20pct dev baseline (Phase 1)."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from continuum.eval.benchmark.scoring import score_answer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = (
    ROOT / "data/evals/benchmark-v1/subset-20pct/runs/subset-20pct-baseline-001/continuum/results.jsonl"
)
DEFAULT_QUESTIONS = ROOT / "data/evals/benchmark-v1/subset-20pct/questions.jsonl"
DEFAULT_DEV_IDS = ROOT / "data/evals/benchmark-v1/subset-20pct/samples/sample_dev.json"

_PRONOUN_RE = re.compile(r"\b(she|he|they|their|her|his|them)\b", re.I)
_TEMPORAL_RE = re.compile(
    r"\b(current|previous|formerly|as of|before|after|when did|owner|handoff|transfer)\b",
    re.I,
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_USERNAME_RE = re.compile(r"@[A-Za-z0-9_.-]+")
_SLUG_RE = re.compile(r"\b[a-z]+(?:-[a-z]+)+\b")
_COMPANY_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+(?:Corp|Inc|LLC|Ltd|Co)\.?)?)\b")
_MULTI_NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _cluster_question(question_text: str) -> list[str]:
    text = question_text or ""
    clusters: list[str] = []
    if _EMAIL_RE.search(text) or _USERNAME_RE.search(text):
        clusters.append("person_alias")
    names = [
        m
        for m in _MULTI_NAME_RE.findall(text)
        if m.lower() not in {"who", "what", "when", "where", "which", "the", "and", "for", "from", "with"}
    ]
    if len(names) >= 2 or " or " in text.lower():
        clusters.append("multi_entity_ambiguity")
    if _PRONOUN_RE.search(text):
        clusters.append("pronouns")
    if _TEMPORAL_RE.search(text):
        clusters.append("temporal_owner")
    if _SLUG_RE.search(text) or "project" in text.lower() or "repo" in text.lower():
        clusters.append("project_names")
    if any(w in text.lower() for w in ("account", "customer", "client", "company", "corp")):
        clusters.append("company_alias")
    if not clusters:
        if names:
            clusters.append("person_alias")
        else:
            clusters.append("other")
    return clusters


def analyze(
    *,
    results_path: Path,
    questions_path: Path,
    dev_ids_path: Path,
) -> dict:
    dev_ids = set(json.loads(dev_ids_path.read_text(encoding="utf-8")))
    questions_by_id = {str(q["question_id"]): q for q in _load_jsonl(questions_path)}
    rows = _load_jsonl(results_path)
    rows = [r for r in rows if str(r["question_id"]) in dev_ids]

    failures: list[dict] = []
    for row in rows:
        qid = str(row["question_id"])
        question = questions_by_id[qid]
        gold = str(question.get("gold_answer", ""))
        answer = str(row.get("answer", ""))
        correct = score_answer(answer, gold)
        if correct and answer.strip():
            continue
        expected = set(question.get("expected_doc_ids") or ())
        retrieved = set(row.get("retrieved_artifacts") or ())
        retrieval_ok = bool(expected & retrieved) if expected else bool(retrieved)
        clusters = _cluster_question(str(question.get("question", "")))
        failures.append(
            {
                "question_id": qid,
                "question_type": question.get("question_type"),
                "clusters": clusters,
                "retrieval_ok": retrieval_ok,
                "retrieval_miss": bool(expected) and not retrieval_ok,
                "question": question.get("question", "")[:120],
            }
        )

    cluster_counts: Counter[str] = Counter()
    for item in failures:
        for cluster in item["clusters"]:
            cluster_counts[cluster] += 1

    total_failures = len(failures)
    ranked = cluster_counts.most_common()
    cumulative = 0
    top_patterns: list[dict] = []
    for name, count in ranked:
        cumulative += count
        top_patterns.append(
            {
                "pattern": name,
                "count": count,
                "pct_of_failures": round(100 * count / total_failures, 1) if total_failures else 0,
                "examples": [f["question_id"] for f in failures if name in f["clusters"]][:5],
            }
        )

    retrieval_ok_er = sum(1 for f in failures if f["retrieval_ok"])
    retrieval_miss = sum(1 for f in failures if f["retrieval_miss"])

    return {
        "total_dev": len(rows),
        "total_failures": total_failures,
        "retrieval_ok_wrong_answer": retrieval_ok_er,
        "retrieval_miss": retrieval_miss,
        "cluster_counts": dict(cluster_counts),
        "top_patterns": top_patterns,
        "failures": failures,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Benchmark ER v1 — Failure Clusters (Phase 1)",
        "",
        "Source run: `subset-20pct-baseline-001` (dev 80Q, full-v1 corpus, `--no-graph`).",
        "",
        "**Classifier caveat:** coarse `ENTITY_RESOLUTION_FAILURE` labels are inflated when graph is disabled.",
        "This doc uses trace fields (`retrieved_artifacts`, gold overlap) and question-text patterns.",
        "",
        f"- Dev questions: {report['total_dev']}",
        f"- Failures analyzed: {report['total_failures']}",
        f"- Retrieval OK but wrong answer: {report['retrieval_ok_wrong_answer']}",
        f"- Retrieval miss (gold doc not retrieved): {report['retrieval_miss']}",
        "",
        "## Pattern table",
        "",
        "| Pattern | Count | % of failures | Example question_ids |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in report["top_patterns"]:
        examples = ", ".join(item["examples"])
        lines.append(
            f"| {item['pattern']} | {item['count']} | {item['pct_of_failures']} | {examples} |"
        )

    lines.extend(["", "## Top patterns covering 80%"])
    cumulative = 0
    covering: list[str] = []
    total = report["total_failures"] or 1
    for item in report["top_patterns"]:
        cumulative += item["count"]
        covering.append(item["pattern"])
        if cumulative / total >= 0.8:
            break
    lines.append(f"Patterns: **{', '.join(covering)}** cover ≥80% of failure mentions.")
    lines.append("")
    lines.append("## Retrieval vs resolution")
    lines.append("")
    lines.append("| Bucket | Count |")
    lines.append("| --- | ---: |")
    lines.append(f"| Retrieval OK, answer wrong | {report['retrieval_ok_wrong_answer']} |")
    lines.append(f"| Retrieval miss | {report['retrieval_miss']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--dev-ids", type=Path, default=DEFAULT_DEV_IDS)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs/benchmark-er-v1-failure-clusters.md",
    )
    args = parser.parse_args()

    report = analyze(
        results_path=args.results,
        questions_path=args.questions,
        dev_ids_path=args.dev_ids,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_markdown(report), encoding="utf-8")
    json_path = args.out.with_suffix(".json")
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "total_failures": report["total_failures"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
