"""Phase 4: deep diagnostic analysis of the full-v1-100 checkpoint.

Builds the retrieval x answer 2x2 matrix, then drills into:
  - retrieval misses (46): query<->gold-doc token overlap, gold-answer presence,
    gold doc source/length
  - retrieval-hit / answer-wrong (~40): gold vs model answer comparison
  - question-type and source distributions
  - latency profile

Reads the corpus zip to fetch gold documents by dsid. Does NOT modify
the checkpoint.
"""

import json
import re
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, ".")
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, load_questions
from continuum.eval.benchmark.scoring import score_answer, score_document_recall

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
ZIP = Path("data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip")

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
STOP = set("the a an and or of to in for on with by from at as is are was were be been being this that these those it its it's".split())


def toks(text):
    return [t.lower() for t in TOKEN_RE.findall(text)]


def tok_overlap(a, b):
    ta, tb = set(toks(a)), set(toks(b))
    return len(ta & tb) / max(len(ta), 1), len(ta & tb)


rows = [json.loads(l) for l in (CK / "bm25" / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
answers = [json.loads(l) for l in (CK / "answers_report.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
questions = load_questions("full-v1", DEFAULT_BENCHMARK_ROOT)
qby = {str(q["question_id"]): q for q in questions}
answer_by_id = {str(a["question_id"]): a for a in answers}

print(f"checkpoint rows: {len(rows)}  questions loaded: {len(questions)}")

matrix = Counter()
by_qtype = defaultdict(Counter)
by_source = defaultdict(Counter)
lat = {"total_ms": [], "retrieval_ms": [], "gen_ms": []}
for r in rows:
    qid = str(r["question_id"])
    q = qby[qid]
    rec = score_document_recall(r.get("retrieved_artifacts") or [], q.get("expected_doc_ids") or [])
    rec = rec if rec is not None else 0.0
    hit = rec > 0
    ok = score_answer(str(r.get("answer", "")), str(q.get("gold_answer", "")))
    key = ("HIT" if hit else "MISS") + "/" + ("CORRECT" if ok else "WRONG")
    matrix[key] += 1
    by_qtype[q.get("question_type", "?")][key] += 1
    for s in (q.get("source_types") or ["?"]):
        by_source[s][key] += 1
    lat["total_ms"].append(float(r.get("latency_ms") or 0))
    lat["retrieval_ms"].append(float((r.get("latency_breakdown") or {}).get("retrieval_ms") or 0))
    lat["gen_ms"].append(float((r.get("latency_breakdown") or {}).get("generation_ms") or 0))

print("\n=== 2x2 MATRIX (retrieval x answer) ===")
print(f"{'':12} {'CORRECT':>8} {'WRONG':>8} {'TOTAL':>8}")
for rh in ("HIT", "MISS"):
    print(f"{rh:12} {matrix[rh+'/CORRECT']:>8} {matrix[rh+'/WRONG']:>8} {matrix[rh+'/CORRECT'] + matrix[rh+'/WRONG']:>8}")
tot_c = matrix["HIT/CORRECT"] + matrix["MISS/CORRECT"]
print(f"{'TOTAL':12} {tot_c:>8} {100 - tot_c:>8} {100:>8}")

print("\n=== by question type ===")
for qt, c in sorted(by_qtype.items()):
    print(f"  {qt:>28}: {dict(c)}")

print("\n=== by source ===")
for s, c in sorted(by_source.items()):
    print(f"  {s:>28}: {dict(c)}")

print("\n=== latency ===")
for stage, vals in lat.items():
    vals = [v for v in vals if v > 0]
    if vals:
        print(f"  {stage:>12}: n={len(vals)} median={statistics.median(vals)/1000:.1f}s mean={statistics.mean(vals)/1000:.1f}s p95={sorted(vals)[int(len(vals)*0.95)-1]/1000:.1f}s")

misses = [r for r in rows if score_document_recall(r.get("retrieved_artifacts") or [], qby[str(r["question_id"])].get("expected_doc_ids") or []) in (0, None)]
hits_wrong = [r for r in rows if (score_document_recall(r.get("retrieved_artifacts") or [], qby[str(r["question_id"])].get("expected_doc_ids") or []) or 0) > 0 and not score_answer(str(r.get("answer", "")), str(qby[str(r["question_id"])].get("gold_answer", "")))]

print(f"\n=== retrieval MISSES: {len(misses)} ===")
print("expected_doc_ids count dist:", dict(Counter(len(qby[str(r['question_id'])].get('expected_doc_ids') or []) for r in misses)))
print("zero-expected-doc questions among misses:", sum(1 for r in misses if not qby[str(r['question_id'])].get('expected_doc_ids')))

print(f"\n=== retrieval HIT but answer WRONG: {len(hits_wrong)} ===")
print("expected_doc_ids count dist:", dict(Counter(len(qby[str(r['question_id'])].get('expected_doc_ids') or []) for r in hits_wrong)))

result = {
    "matrix": dict(matrix),
    "by_qtype": {k: dict(v) for k, v in by_qtype.items()},
    "by_source": {k: dict(v) for k, v in by_source.items()},
    "latency": {k: {"median_s": round(statistics.median([v for v in vals if v > 0])/1000, 2) if [v for v in vals if v > 0] else None} for k, vals in lat.items()},
    "miss_count": len(misses),
    "hit_wrong_count": len(hits_wrong),
}
print("\nresult:", json.dumps(result, indent=2))