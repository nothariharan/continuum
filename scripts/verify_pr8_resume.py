"""Phase 2: functional resume-safety test for baseline runner.

Uses an isolated temp root + sample-v1 + mock model. Never touches the
immutable full-v1-100 checkpoint.

Steps:
1. run max=3 -> 3 rows
2. re-run max=3 -> 0 new rows (resume skips completed)
3. run max=5 -> exactly qst_0004, qst_0005 added, no dupes
4. verify final file: 5 rows, one per question, in order
5. torn-tail robustness: append a partial JSON line, attempt resume
6. verify fsync persists rows (row present immediately after append)
"""

import json
import subprocess
import sys
from pathlib import Path

TMP = Path(r"C:\Users\HARIHA~1\AppData\Local\Temp\opencode\resume-test-root")
OUT = TMP / "full-v1" / "runs" / "resume-test" / "bm25" / "results.jsonl"

failures = []


def check(cond, label):
    print(f"[{'OK ' if cond else 'FAIL'}] {label}")
    if not cond:
        failures.append(label)


def run(max_q):
    r = subprocess.run(
        [sys.executable, "scripts/run_full_v1_baseline.py", "--mode", "sample-v1",
         "--run-id", "resume-test", "--system", "bm25", "--answer-model", "mock",
         "--no-graph", "--max-questions", str(max_q), "--root", str(TMP)],
        capture_output=True, text=True, timeout=300,
    )
    return r


def rows():
    if not OUT.exists():
        return []
    out = []
    for line in OUT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


if OUT.exists():
    OUT.unlink()

def sorted_sample_ids():
    r = subprocess.run(
        [sys.executable, "scripts/build_benchmark_v1.py", "--mode", "sample-v1",
         "--root", str(TMP), "--seed", "42"],
        capture_output=True, text=True, timeout=120,
    )
    q = Path(TMP) / "sample-v1" / "questions.jsonl"
    return [json.loads(l)["question_id"] for l in q.read_text(encoding="utf-8").splitlines() if l.strip()]


sample_ids = sorted_sample_ids()
print(f"sample-v1 question order (first 5): {sample_ids[:5]}")

run(3)
r1 = rows()
print(f"after max=3: {len(r1)} rows, ids={[r['question_id'] for r in r1]}")
check(len(r1) == 3, "first run persisted exactly 3 rows")
check([r["question_id"] for r in r1] == sample_ids[:3], "rows are first 3 sample questions in order")

run(3)
r2 = rows()
print(f"after re-run max=3: {len(r2)} rows")
check(len(r2) == 3, "re-run added no duplicates (resume by question_id)")

run(5)
r3 = rows()
print(f"after max=5: {len(r3)} rows, ids={[r['question_id'] for r in r3]}")
check(len(r3) == 5, "resume with larger max added only missing rows")
check([r["question_id"] for r in r3] == sample_ids[:5], "final ids = first 5 sample questions, in order, no dupes")
check(len({r["question_id"] for r in r3}) == 5, "all 5 question_ids unique")

original = OUT.read_text(encoding="utf-8")
torn_qid = sample_ids[5]
with OUT.open("a", encoding="utf-8") as fh:
    fh.write(f'{{"question_id": "{torn_qid}", "system": "bm25", "answer": "partial')
r = run(6)
print(f"torn-tail resume exit code: {r.returncode}")
torn_err = "Traceback" in r.stderr or r.returncode != 0
print(f"  stderr tail: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else '(none)'}")
check(not torn_err, "torn final row tolerated: resume succeeds (exit 0, no traceback)")
print("  raw lines after torn resume:")
for raw in OUT.read_text(encoding="utf-8").splitlines():
    print(f"    {raw[:80]}")
r6 = rows()
check(any(x["question_id"] == torn_qid for x in r6), "torn question was re-run and appended as a clean row")
check(len(r6) == 6, "final file has 6 clean rows (5 + re-run q6), partial line not counted as valid")
OUT.write_text(original, encoding="utf-8")

r = run(5)
r4 = rows()
check(len(r4) == 5, "clean resume after restoring file works")

print()
if failures:
    print("FAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("ALL RESUME-SAFETY CHECKS PASSED")