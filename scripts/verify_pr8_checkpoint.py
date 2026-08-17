"""Independent checkpoint integrity verification (Phase 2).

Verifies the full-v1-100 checkpoint is internally consistent and immutable
(no regeneration - validation only).

Checks:
1. bm25/results.jsonl: 100 rows, qst_0001..qst_0100 contiguous, no dupes, valid JSON
2. answers_report.jsonl: same 100 question_ids
3. analysis_summary.json: consistent with results (13 correct, 54% recall, 46 zero-recall)
4. profile_100.json: latency consistent with results rows
5. run_manifest.json: config fields
6. checkpoint_sha256.json: recompute and compare for the 5 covered files
7. raw-backup-run-dir: 101 rows, first 100 identical to checkpoint results
"""

import hashlib
import json
import statistics
import sys
from pathlib import Path

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
failures = []


def check(cond, label):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {label}")
    if not cond:
        failures.append(label)


def load_jsonl(p):
    rows = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            failures.append(f"malformed JSON line {i} in {p}: {e}")
            continue
    return rows


results = load_jsonl(CK / "bm25" / "results.jsonl")
print(f"results.jsonl rows: {len(results)}")
qids = [r["question_id"] for r in results]
expected = [f"qst_{i:04d}" for i in range(1, 101)]
check(len(results) == 100, "exactly 100 result records")
check(qids == expected, "qst_0001..qst_0100 contiguous, ordered, no dupes/missing")
check(len(set(qids)) == 100, "all 100 question_ids unique")

answers = load_jsonl(CK / "answers_report.jsonl")
print(f"answers_report rows: {len(answers)}")
aqids = [r["question_id"] for r in answers]
check(len(answers) == 100, "answers_report has exactly 100 rows")
check(aqids == expected, "answers_report covers same qst_0001..qst_0100 in order")

backup = load_jsonl(CK / "raw-backup-run-dir" / "results-101-complete.jsonl")
print(f"raw backup rows: {len(backup)}")
bqids = [r["question_id"] for r in backup]
check(len(backup) == 101, "raw backup has 101 persisted rows")
check(bqids == expected + ["qst_0101"], "backup = qst_0001..qst_0101")
check(backup[:100] == results, "backup first 100 rows identical to checkpoint results")

analysis = json.loads((CK / "analysis_summary.json").read_text(encoding="utf-8"))
score = analysis["official_score_100q"]
check(score["question_count"] == 100, "analysis_summary question_count == 100")
check(score["answer_correctness"] == 0.13, f"answer_correctness == 0.13 (got {score['answer_correctness']})")
check(abs(score["document_recall_mean"] - 0.54) < 1e-9, f"doc recall mean == 0.54 (got {score['document_recall_mean']})")
check(analysis["by_question_type"]["basic"]["count"] == 100, "by_question_type basic == 100")

correct_ids = {qid for qid, r in zip(qids, results) if r.get("answer_correct")}
print(f"rows with answer_correct=True: {len(correct_ids)} ({sorted(correct_ids)})")

zero_recall = sum(1 for r in results if (r.get("recall") or 0) == 0.0)
print(f"rows with recall==0: {zero_recall}")
check(zero_recall == 46, "46 zero-recall questions (from raw results)")

lat_ms = [float(r.get("latency_ms") or 0) for r in results]
ret_ms = [float((r.get("latency_breakdown") or {}).get("retrieval_ms") or 0) for r in results]
gen_ms = [float((r.get("latency_breakdown") or {}).get("generation_ms") or 0) for r in results]
prof = json.loads((CK / "profile_100.json").read_text(encoding="utf-8"))
check(abs(statistics.median(lat_ms) / 1000 - prof["overall_total_latency"]["median_s"]) < 0.01, "profile median total latency matches results")
check(abs(statistics.median(ret_ms) / 1000 - prof["stage_latency"]["retrieval_ms"]["median_s"]) < 0.01, "profile median retrieval latency matches results")
check(abs(statistics.median(gen_ms) / 1000 - prof["stage_latency"]["generation_ms"]["median_s"]) < 0.01, "profile median generation latency matches results")

sha = json.loads((CK / "checkpoint_sha256.json").read_text(encoding="utf-8"))
covered = 0
for rel, expected_sha in sorted(sha.items()):
    p = CK / rel
    if not p.exists():
        failures.append(f"sha manifest references missing file: {rel}")
        continue
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    covered += 1
    print(f"  {rel}: {'OK ' if actual == expected_sha else 'FAIL'}")
    if actual != expected_sha:
        failures.append(f"sha mismatch: {rel}")
check(covered == len(sha), f"all {len(sha)} manifest files verified")
uncovered = [str(p.relative_to(CK)) for p in CK.rglob("*") if p.is_file() and str(p.relative_to(CK)) not in sha]
print(f"files NOT covered by sha manifest: {uncovered}")

manifest = json.loads((CK / "run_manifest.json").read_text(encoding="utf-8"))
check(manifest["run_id"] == "full-v1-baseline-001", "run_manifest run_id correct")
check(manifest["answer_model"] == "accounts/fireworks/models/gpt-oss-20b", "run_manifest answer model correct")
check(manifest["corpus_records_loaded"] == 511962, "run_manifest corpus records == 511962")
check(manifest["top_k"] == 5, "run_manifest top_k == 5")
check(manifest["temperature"] == 0.0, "run_manifest temperature == 0.0")
check(manifest["with_graph"] is False, "run_manifest with_graph == False")
check(manifest["question_count"] == 500, "run_manifest question_count == 500")

meta = json.loads((CK / "checkpoint_metadata.json").read_text(encoding="utf-8"))
check(meta["checkpoint_questions"] == 100, "metadata checkpoint_questions == 100")
check(meta["integrity"]["checkpoint_records"] == 100 and meta["integrity"]["unique_ids"] == 100 and meta["integrity"]["duplicates"] == 0, "metadata integrity block consistent")
check(meta["resume_from_question"] == "qst_0101", "metadata resume_from qst_0101")

print()
if failures:
    print("FAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("ALL CHECKPOINT CHECKS PASSED")
