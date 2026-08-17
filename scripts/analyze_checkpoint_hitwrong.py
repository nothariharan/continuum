"""Phase 4: hit/wrong answer analysis + miss ranking diagnosis (single zip pass)."""

import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, ".")
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, load_questions
from continuum.eval.benchmark.scoring import normalize_text, score_answer, score_document_recall

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
ZIP = Path("data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip")
TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")

rows = [json.loads(l) for l in (CK / "bm25" / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
questions = load_questions("full-v1", DEFAULT_BENCHMARK_ROOT)
qby = {str(q["question_id"]): q for q in questions}

with zipfile.ZipFile(ZIP) as zf:
    names = zf.namelist()
dsid_path = {}
for n in names:
    m = re.match(r"(dsid_[0-9a-f]{32})__", n.rsplit("/", 1)[-1])
    if m:
        dsid_path[m.group(1)] = n

needed = set()
for r in rows:
    qid = str(r["question_id"])
    q = qby[qid]
    needed.update(q.get("expected_doc_ids") or [])
    needed.update(r.get("retrieved_artifacts") or [])
cache = {}
with zipfile.ZipFile(ZIP) as zf:
    for d in needed:
        p = dsid_path.get(d)
        if p:
            cache[d] = zf.read(p).decode("utf-8", errors="replace")
print(f"docs cached from zip: {len(cache)}")

def toks(text):
    return [t.lower() for t in TOKEN_RE.findall(text)]

def q_overlap(qtext, content):
    qt = set(toks(qtext))
    ct = set(toks(content))
    return len(qt & ct) / max(len(qt), 1)

print("=== PART A: 45 retrieval-hit / answer-wrong cases ===")
hw = []
for r in rows:
    qid = str(r["question_id"])
    q = qby[qid]
    rec = score_document_recall(r.get("retrieved_artifacts") or [], q.get("expected_doc_ids") or [])
    if (rec or 0) > 0 and not score_answer(str(r.get("answer", "")), str(q.get("gold_answer", ""))):
        gold = normalize_text(q["gold_answer"])
        got = normalize_text(r.get("answer", ""))
        gtok = set(gold.split())
        overlap = len(gtok & set(got.split())) / len(gtok) if gtok else 0.0
        hw.append({"qid": qid, "overlap": round(overlap, 3), "gold_len": len(gold.split()),
                   "got_len": len(got.split()), "question": q["question"][:120]})
print(f"count: {len(hw)}")
b = Counter()
for h in hw:
    o = h["overlap"]
    bucket = ">=0.6 near-correct" if o >= 0.6 else ("0.4-0.6 near-miss" if o >= 0.4 else ("0.2-0.4 partial" if o >= 0.2 else "<0.2 wrong"))
    b[bucket] += 1
for k, v in b.most_common():
    print(f"  {k:>22}: {v}")

print("\nnear-miss examples (0.4-0.6):")
for h in [h for h in hw if 0.4 <= h["overlap"] < 0.6][:6]:
    print(f"  {h['qid']} overlap={h['overlap']:.2f} Q: {h['question']}")
print("\nclearly-wrong examples (<0.2):")
for h in [h for h in hw if h["overlap"] < 0.2][:6]:
    print(f"  {h['qid']} overlap={h['overlap']:.2f} Q: {h['question']}")

print("\n=== PART B: ranking diagnosis for 46 misses ===")
miss_stats = []
for r in rows:
    qid = str(r["question_id"])
    q = qby[qid]
    rec = score_document_recall(r.get("retrieved_artifacts") or [], q.get("expected_doc_ids") or [])
    if rec in (0, None) and q.get("expected_doc_ids"):
        qtext = str(q["question"])
        exp = q["expected_doc_ids"][0]
        gold_overlap = q_overlap(qtext, cache.get(exp, "")) if exp in cache else None
        ret_overlaps = [q_overlap(qtext, cache[rid]) for rid in (r.get("retrieved_artifacts") or [])[:5] if rid in cache]
        avg_ret = sum(ret_overlaps) / max(len(ret_overlaps), 1) if ret_overlaps else None
        miss_stats.append({"qid": qid, "gold_overlap": gold_overlap,
                           "retrieved_max": max(ret_overlaps) if ret_overlaps else None,
                           "retrieved_avg": avg_ret})

print(f"misses: {len(miss_stats)}")
pairs = [m for m in miss_stats if m["gold_overlap"] is not None and m["retrieved_avg"] is not None]
print(f"gold overlap >= retrieved avg (gold NOT clearly worse than what was retrieved): "
      f"{sum(1 for m in pairs if m['gold_overlap'] >= m['retrieved_avg'])} / {len(pairs)}")
print(f"gold overlap > retrieved MAX: "
      f"{sum(1 for m in pairs if m['retrieved_max'] is not None and m['gold_overlap'] > m['retrieved_max'])} / {len(miss_stats)}")
print("gold overlap > 0.5 but still missed top-5:",
      sum(1 for m in miss_stats if m["gold_overlap"] is not None and m["gold_overlap"] > 0.5))
print("gold overlap > 0.6 but still missed top-5:",
      sum(1 for m in miss_stats if m["gold_overlap"] is not None and m["gold_overlap"] > 0.6))
print("\nexample miss where gold has HIGH overlap but was outranked:")
for m in [m for m in miss_stats if m["gold_overlap"] is not None and m["gold_overlap"] > 0.6][:6]:
    print(f"  {m['qid']} gold_overlap={m['gold_overlap']:.2f} retrieved_avg={m['retrieved_avg']:.2f} retrieved_max={m['retrieved_max']:.2f}")

Path("data/metadata/pr8_review_hitwrong_analysis.json").write_text(
    json.dumps({"hit_wrong": hw, "miss_ranking": miss_stats}, indent=2, default=str), encoding="utf-8")
print("\nsaved -> data/metadata/pr8_review_hitwrong_analysis.json")