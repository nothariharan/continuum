"""Phase 4: semantic diff between repo questions.jsonl and official zip questions.jsonl."""

import json
import sys
import zipfile
from pathlib import Path

ZIP = Path("data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip")
REPO_Q = Path("data/evals/benchmark-v1/full-v1/questions.jsonl")

with zipfile.ZipFile(ZIP) as zf:
    zip_q = [json.loads(l) for l in zf.read("questions.jsonl").decode("utf-8").splitlines() if l.strip()]
repo_q = [json.loads(l) for l in REPO_Q.read_text(encoding="utf-8").splitlines() if l.strip()]

print(f"zip keys per q: {sorted(zip_q[0].keys())}")
print(f"repo keys per q: {sorted(repo_q[0].keys())}")

diff_fields = {}
q_diffs = 0
example = None
for z, r in zip(zip_q, repo_q):
    assert z["question_id"] == r["question_id"]
    for field in set(z) | set(r):
        zv = z.get(field)
        rv = r.get(field)
        if zv != rv:
            diff_fields.setdefault(field, 0)
            diff_fields[field] += 1
            q_diffs += 1
            if example is None:
                example = (z["question_id"], field, zv, rv)

print(f"questions with any field difference: {q_diffs}")
print(f"fields differing: {dict(diff_fields)}")
if example:
    qid, field, zv, rv = example
    print(f"\nfirst example: {qid} field={field}")
    print(f"  zip : {str(zv)[:400]}")
    print(f"  repo: {str(rv)[:400]}")
