"""Audit the 13 scored-correct rows: genuine vs empty-answer artifacts."""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, load_questions
from continuum.eval.benchmark.scoring import score_answer, score_document_recall

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
rows = [json.loads(l) for l in (CK / "bm25" / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
questions = load_questions("full-v1", DEFAULT_BENCHMARK_ROOT)
qby = {str(q["question_id"]): q for q in questions}

print("all 13 scored-correct rows:")
genuine = 0
empty = 0
for r in rows:
    qid = str(r["question_id"])
    q = qby[qid]
    if score_answer(str(r.get("answer", "")), str(q.get("gold_answer", ""))):
        ans = str(r.get("answer") or "").strip()
        rec = score_document_recall(r.get("retrieved_artifacts") or [], q.get("expected_doc_ids") or [])
        err = r.get("error")
        kind = "EMPTY-ANSWER ARTIFACT" if len(ans) == 0 else "GENUINE"
        if len(ans) == 0:
            empty += 1
        else:
            genuine += 1
        print(f"  {qid} recall={rec} {kind} error={bool(err)}")
        if err:
            print("      error:", str(err)[:140])

print(f"\n=> genuine correct answers: {genuine}  empty-answer artifacts: {empty}")
print(f"=> true answer_correctness if empty answers excluded: {genuine}/100 = {genuine/100:.2%}")