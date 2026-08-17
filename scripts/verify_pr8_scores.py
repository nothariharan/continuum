"""Independently recompute checkpoint scores (13%, 54%, 46) from raw rows.

Uses the repo's official scoring functions on checkpoint rows + official questions,
and cross-checks against analysis_summary.json.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, load_questions
from continuum.eval.benchmark.scoring import score_answer, score_document_recall, score_rows

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
rows = [json.loads(l) for l in (CK / "bm25" / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
questions = load_questions("full-v1", DEFAULT_BENCHMARK_ROOT)
qby = {str(q["question_id"]): q for q in questions}

print(f"questions loaded: {len(questions)}, checkpoint rows: {len(rows)}")

correct = 0
recalls = []
zero = 0
errors = 0
row_qids = set()
for r in rows:
    qid = str(r["question_id"])
    row_qids.add(qid)
    q = qby[qid]
    ans_ok = score_answer(str(r.get("answer", "")), str(q.get("gold_answer", "")))
    if ans_ok:
        correct += 1
    rec = score_document_recall(r.get("retrieved_artifacts") or [], q.get("expected_doc_ids") or [])
    recalls.append(rec if rec is not None else 0.0)
    if rec == 0.0:
        zero += 1
    if r.get("error"):
        errors += 1

n = len(rows)
print(f"recomputed answer correctness: {correct}/{n} = {correct/n:.4f}")
print(f"recomputed mean doc recall:   {sum(recalls)/n:.4f}")
print(f"recomputed zero-recall count: {zero}")
print(f"errors in rows:               {errors}")
print(f"rows map to loaded questions: {len(row_qids)}/{n}")

official = score_rows(rows, qby)
print(f"official score_rows: {official}")
summary = json.loads((CK / "analysis_summary.json").read_text(encoding="utf-8"))["official_score_100q"]
print(f"analysis_summary:    {summary}")

mismatch = []
for k in ("answer_correctness", "document_recall_mean"):
    if abs(official.get(k, 0) - summary.get(k, 0)) > 1e-9:
        mismatch.append(k)
print("MATCH" if not mismatch and correct == 13 and zero == 46 else f"MISMATCH: {mismatch}")
sys.exit(0 if not mismatch and correct == 13 and zero == 46 else 1)
