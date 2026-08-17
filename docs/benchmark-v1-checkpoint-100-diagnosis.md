# FULL-V1 PARTIAL CHECKPOINT — 100/500

**This is NOT the final public benchmark score.**

Diagnostic checkpoint from the first official full-corpus BM25 leg (`full-v1-baseline-001`).

## Checkpoint artifacts

```
data/evals/benchmark-v1/checkpoints/full-v1-100/
  bm25/results.jsonl              # immutable first 100 questions
  raw-backup-run-dir/             # full persisted run at stop time (101 rows)
  run_manifest.json
  checkpoint_metadata.json
  profile_100.json
  checkpoint_sha256.json
```

Live run directory (resumable, do not delete):

```
data/evals/benchmark-v1/full-v1/runs/full-v1-baseline-001/
  bm25/results.jsonl              # 101 rows at stop (qst_0001–qst_0101)
  run_manifest.json
```

## Run configuration (frozen)

| Field | Value |
|---|---|
| Git commit | `1340de98472428e8ad689ce9bbcf07ba54a8a96e` |
| Run ID | `full-v1-baseline-001` |
| System | BM25 only (leg 1 of 4) |
| Corpus | 511,962 docs (EnterpriseRAG-Bench v1.0.0) |
| Questions | 100 checkpoint / 500 official |
| Answer model | `accounts/fireworks/models/gpt-oss-20b` |
| Command | `PYTHONPATH=. python scripts/run_full_v1_baseline.py --run-id full-v1-baseline-001 --system bm25 --answer-model real --no-graph --fail-on-fallback` |

## Integrity at stop

| Check | Result |
|---|---|
| Checkpoint records | 100 |
| Unique question IDs | 100 |
| Malformed JSON | 0 |
| Duplicates | 0 |
| Persisted before stop | 101 (qst_0101 also complete) |

## Performance diagnosis (100 questions)

| Stage | Median | Mean | p95 |
|---|---|---|---|
| **Total** | 378 s | 379 s | 560 s |
| **Retrieval (BM25 get_scores over 512K)** | 372 s | 375 s | 556 s |
| **Answer model (Fireworks)** | 3.0 s | 3.7 s | 7.2 s |

### Root cause

**Not LLM inference.** Each question calls `BM25Okapi.get_scores()` over all **511,962** documents, then sorts the full score vector. That is ~6 minutes of CPU per question on this machine.

Initialization (once per process):

- Corpus load + tokenization for BM25 index build (~30 min before Q1)

Inside loop (per question):

- Full-corpus BM25 scoring (dominant)
- LLM generation (~3 s)

### Optimization direction (Phase 8 — not applied yet)

- Do **not** change scoring or answer semantics
- Speed up retrieval without changing top-k fairness:
  - persistent lexical index
  - candidate pruning / inverted index
  - avoid full `get_scores()` over 512K every query
- Initialize corpus + indexes **once** per system leg (already true)
- Resume from Q101 without re-running Q1–Q100

## Resume

```bash
PYTHONPATH=. python scripts/run_full_v1_baseline.py \
  --run-id full-v1-baseline-001 \
  --system bm25 \
  --answer-model real \
  --no-graph \
  --fail-on-fallback
```

Skips any `question_id` already present in `results.jsonl`. Next question: **qst_0102**.

## Next steps

1. Optimize BM25 retrieval (same semantics, faster index lookup)
2. Validate on first 20–50 checkpoint questions (answers unchanged)
3. Resume BM25 Q102–Q500
4. Run dense / hybrid / continuum legs with same checkpoint/resume pattern
