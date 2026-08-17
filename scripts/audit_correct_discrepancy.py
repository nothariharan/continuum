"""Compare PR-documented correct list vs actual score_answer output on checkpoint."""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, load_questions
from continuum.eval.benchmark.scoring import score_answer, score_document_recall

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
rows = [json.loads(l) for l in (CK / "bm25" / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
answers = [json.loads(l) for l in (CK / "answers_report.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
questions = load_questions("full-v1", DEFAULT_BENCHMARK_ROOT)
qby = {str(q["question_id"]): q for q in questions}

pr_correct = {"qst_0018","qst_0022","qst_0033","qst_0035","qst_0036","qst_0037","qst_0040","qst_0043","qst_0047","qst_0054","qst_0067","qst_0078","qst_0094"}
by_id = {str(r["question_id"]): r for r in rows}
actual_correct = {str(r["question_id"]) for r in rows if score_answer(str(r.get("answer","")), str(qby[str(r["question_id"])].get("gold_answer","")))}

print("PR-documented correct but NOT scored-correct on results.jsonl:")
for qid in sorted(pr_correct - actual_correct):
    r = by_id[qid]
    ans = str(r.get("answer") or "").strip()
    print(f"  {qid} ans_len={len(ans)} ans_head={ans[:100]!r}")

print("\nscored-correct on results.jsonl but NOT in PR list:")
for qid in sorted(actual_correct - pr_correct):
    r = by_id[qid]
    ans = str(r.get("answer") or "").strip()
    print(f"  {qid} ans_len={len(ans)} ans_head={ans[:100]!r}")

print("\nanswers_report-based score_answer (gold vs reported answer):")
rep = {str(a["question_id"]): a for a in answers}
rep_correct = {qid for r in rows for qid in [str(r["question_id"])] if score_answer(str(rep.get(str(r["question_id"]), {}).get("model_answer", r.get("answer", ""))), str(qby[str(r["question_id"])].get("gold_answer","")))}
print("  answers_report keys:", sorted(rep.keys())[:3], "...")
print("  rep-scored correct set:", sorted(rep_correct))
print("  rep-scored correct == results-scored correct:", rep_correct == actual_correct)

print("\nscore_answer discrepancy detail (results vs report):")
for qid in sorted(pr_correct | actual_correct):
    r = by_id[qid]
    a = rep.get(qid, {})
    from_ans = score_answer(str(r.get("answer","")), str(qby[qid].get("gold_answer","")))
    from_rep = score_answer(str(a.get("model_answer", a.get("answer", ""))), str(qby[qid].get("gold_answer","")))
    mark = "  <-- DIFF" if from_ans != from_rep else ""
    print(f"  {qid} results={from_ans} report={from_rep}{mark}")