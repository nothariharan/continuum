"""Phase 4: retrieval-miss deep dive.

For each of the 46 retrieval misses, fetch the gold doc from the zip and
compute:
  - query token overlap with gold doc text
  - whether gold-answer content appears in the gold doc
  - gold doc source + length
  - what BM25 actually retrieved instead (top-5 ids + their sources)
Also classify the miss cause hypothesis.
"""

import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, ".")
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, load_questions
from continuum.eval.benchmark.scoring import score_document_recall

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
ZIP = Path("data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip")

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
STOP = set("the a an and or of to in for on with by from at as is are was were be been being this that these those its it".split())

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

print(f"zip name index built: {len(dsid_path)} dsids indexed")

def toks(text):
    return [t.lower() for t in TOKEN_RE.findall(text)]

misses = []
for r in rows:
    qid = str(r["question_id"])
    q = qby[qid]
    rec = score_document_recall(r.get("retrieved_artifacts") or [], q.get("expected_doc_ids") or [])
    if rec in (0, None) and q.get("expected_doc_ids"):
        misses.append((r, q))

print(f"\n=== {len(misses)} retrieval misses ===\n")
miss_analysis = []
for r, q in misses:
    qid = str(r["question_id"])
    qtext = str(q["question"])
    gold = str(q["gold_answer"])
    exp = q["expected_doc_ids"]
    qtoks = [t for t in toks(qtext) if t not in STOP]
    gtoks = [t for t in toks(gold) if t not in STOP]
    gtoks = [t for t in gtoks if len(t) > 2]
    docs = []
    all_q_overlap = 0.0
    for d in exp:
        path = dsid_path.get(d)
        if not path:
            docs.append({"dsid": d, "missing_in_zip": True})
            continue
        with zipfile.ZipFile(ZIP) as zf:
            content = zf.read(path).decode("utf-8", errors="replace")
        src = path.split("/", 1)[0]
        dtoks = set(toks(content))
        overlap = len(set(qtoks) & dtoks) / max(len(set(qtoks)), 1)
        all_q_overlap = max(all_q_overlap, overlap)
        gold_present = sum(1 for t in gtoks if t in dtoks) / max(len(gtoks), 1)
        docs.append({
            "dsid": d, "source": src, "path": path,
            "len_chars": len(content), "len_tokens": len(dtoks),
            "query_tok_overlap": round(overlap, 3),
            "gold_tok_presence": round(gold_present, 3),
        })
    retrieved_sources = []
    for a in r.get("retrieved_artifacts") or []:
        p = dsid_path.get(a)
        retrieved_sources.append(p.split("/", 1)[0] if p else "?")
    miss_analysis.append({
        "qid": qid,
        "question": qtext[:140],
        "expected": exp,
        "docs": docs,
        "best_query_overlap": round(max(d["query_tok_overlap"] for d in docs if "query_tok_overlap" in d), 3) if any("query_tok_overlap" in d for d in docs) else None,
        "retrieved_sources": dict(Counter(retrieved_sources)),
        "retrieved_ids": (r.get("retrieved_artifacts") or [])[:5],
        "error": r.get("error"),
    })

print("miss questions by expected-doc source:",
      dict(Counter(d["source"] for m in miss_analysis for d in m["docs"] if "source" in d)))
print("\nquery-overlap distribution (best over expected docs):")
ov = sorted(m["best_query_overlap"] for m in miss_analysis if m["best_query_overlap"] is not None)
print(f"  n={len(ov)} min={ov[0]:.3f} median={ov[len(ov)//2]:.3f} max={ov[-1]:.3f}")
low = [m for m in miss_analysis if m["best_query_overlap"] is not None and m["best_query_overlap"] < 0.15]
mid = [m for m in miss_analysis if m["best_query_overlap"] is not None and 0.15 <= m["best_query_overlap"] < 0.35]
high = [m for m in miss_analysis if m["best_query_overlap"] is not None and m["best_query_overlap"] >= 0.35]
print(f"  <0.15: {len(low)}  0.15-0.35: {len(mid)}  >=0.35: {len(high)}")
print(f"  gold-answer-token presence in gold doc (median): "
      f"{sorted(d['gold_tok_presence'] for m in miss_analysis for d in m['docs'] if 'gold_tok_presence' in d)[len([d for m in miss_analysis for d in m['docs'] if 'gold_tok_presence' in d])//2]:.2f}")

print("\n--- example low-overlap misses ---")
for m in low[:8]:
    print(f"  {m['qid']} overlap={m['best_query_overlap']} src={[d.get('source') for d in m['docs']]}")
    print(f"    Q: {m['question']}")
    print(f"    retrieved: {m['retrieved_ids']} ({m['retrieved_sources']})")

Path("data/metadata/pr8_review_miss_analysis.json").write_text(
    json.dumps(miss_analysis, indent=2, default=str), encoding="utf-8")
print("\nsaved -> data/metadata/pr8_review_miss_analysis.json")