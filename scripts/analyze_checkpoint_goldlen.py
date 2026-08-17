"""Phase 4: gold doc length + source comparison (miss vs hit). Single zip pass."""

import json
import re
import statistics
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, ".")
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, load_questions
from continuum.eval.benchmark.scoring import score_document_recall

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
ZIP = Path("data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip")

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

miss_len, hit_len = [], []
miss_src, hit_src = {}, {}
need = {}
for r in rows:
    qid = str(r["question_id"])
    q = qby[qid]
    rec = score_document_recall(r.get("retrieved_artifacts") or [], q.get("expected_doc_ids") or [])
    exp = (q.get("expected_doc_ids") or [])
    if exp and exp[0] in dsid_path:
        need[exp[0]] = (rec in (0, None))
    if exp and exp[0] in dsid_path:
        need[exp[0]] = (rec in (0, None))
with zipfile.ZipFile(ZIP) as zf:
    sizes = {}
    for d, is_miss in need.items():
        p = dsid_path[d]
        sizes[d] = len(zf.read(p))
        src = p.split("/", 1)[0]
        if is_miss:
            miss_len.append(sizes[d]); miss_src[src] = miss_src.get(src, 0) + 1
        else:
            hit_len.append(sizes[d]); hit_src[src] = hit_src.get(src, 0) + 1

print(f"gold doc bytes  MISS: n={len(miss_len)} median={statistics.median(miss_len):,} mean={statistics.mean(miss_len):,.0f}")
print(f"gold doc bytes  HIT : n={len(hit_len)} median={statistics.median(hit_len):,} mean={statistics.mean(hit_len):,.0f}")
print("miss gold source dist:", dict(sorted(miss_src.items(), key=lambda x: -x[1])))
print("hit  gold source dist:", dict(sorted(hit_src.items(), key=lambda x: -x[1])))