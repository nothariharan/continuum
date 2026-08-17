"""Phase 4: verify benchmark question set == official questions in the corpus zip.

Compares:
1. data/evals/benchmark-v1/full-v1/questions.jsonl (committed, used by runner)
2. questions.jsonl inside all_documents.zip (official release copy)
3. recomputed questions_sha256 vs full-v1-question-manifest.json
"""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ZIP = Path("data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip")
REPO_Q = Path("data/evals/benchmark-v1/full-v1/questions.jsonl")
MANIFEST = json.loads(Path("data/evals/benchmark-v1/full-v1/full-v1-question-manifest.json").read_text(encoding="utf-8"))

with zipfile.ZipFile(ZIP) as zf:
    zip_raw = zf.read("questions.jsonl")

repo_raw = REPO_Q.read_bytes()
repo_lf = repo_raw.replace(b"\r\n", b"\n")


def parse(b):
    return [json.loads(l) for l in b.decode("utf-8").splitlines() if l.strip()]


zip_q = parse(zip_raw)
repo_q = parse(repo_lf)

print(f"zip questions:      {len(zip_q)}")
print(f"repo questions:     {len(repo_q)}")

zip_qids = [q["question_id"] for q in zip_q]
repo_qids = [q["question_id"] for q in repo_q]
print(f"zip/repo id order identical: {zip_qids == repo_qids}")

same_content = zip_lf = zip_raw.replace(b"\r\n", b"\n")
sha_zip = hashlib.sha256(zip_lf).hexdigest()
sha_repo = hashlib.sha256(repo_lf).hexdigest()
print(f"sha256(zip questions lf):  {sha_zip}")
print(f"sha256(repo questions lf): {sha_repo}")
print(f"content identical: {sha_zip == sha_repo}")

recomputed = hashlib.sha256(
    "".join(json.dumps(q, sort_keys=True) for q in repo_q).encode()
).hexdigest()
print(f"recomputed manifest sha:   {recomputed}")
print(f"committed manifest sha:    {MANIFEST['questions_sha256']}")
print(f"manifest sha matches:      {recomputed == MANIFEST['questions_sha256']}")
print(f"manifest count:            {MANIFEST['question_count']}")

first = repo_q[0]
print(f"\nsample first question: {first['question_id']} [{first['question_type']}]")
print(f"sample last question:  {repo_q[-1]['question_id']} [{repo_q[-1]['question_type']}]")

ok = (len(zip_q) == 500 and len(repo_q) == 500 and zip_qids == repo_qids
      and sha_zip == sha_repo and recomputed == MANIFEST["questions_sha256"])
print("\nRESULT:", "PASS - question protocol verified" if ok else "FAIL")
sys.exit(0 if ok else 1)
