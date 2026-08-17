# Full-v1 BM25 Checkpoint Results — 100/500 Questions

**Status:** `FULL-V1 PARTIAL CHECKPOINT — 100/500`  
**NOT the final official benchmark.** For founder review before resuming Q101–Q500.

---

## Executive summary

We executed the first real official full-corpus BM25 leg on EnterpriseRAG-Bench v1.0.0:

| Field | Value |
|---|---|
| Corpus | 511,962 documents (full zip, SHA256 verified) |
| Questions completed | **100 / 500** (official order, `qst_0001`–`qst_0100`) |
| System | BM25 RAG only (leg 1 of 4; dense/hybrid/continuum not run yet) |
| Answer model | `accounts/fireworks/models/gpt-oss-20b` (Fireworks, temp=0) |
| Wall-clock | ~9 hours to reach 100 questions |
| Run stopped | Clean SIGTERM after durable checkpoint verified |

### Official-style scores (100 questions only)

| Metric | BM25 (100Q) |
|---|---|
| **Answer correctness** | **13%** (13 / 100) |
| **Document recall (mean)** | **54%** |
| **Invalid extra evidence (mean)** | 0.9 docs/question |
| **Errors** | 1 (`qst_0065`) |

All 100 checkpoint questions are `basic` type (first 100 rows in official manifest order).

---

## What the answers look like

### Correct answers (13 questions)

The model matched gold on **13 / 100** questions under official `score_answer()` semantics (exact/substring/token overlap ≥60%).

Examples:

| ID | Question (truncated) | Gold (truncated) | Model answer (truncated) |
|---|---|---|---|
| `qst_0018` | What is the default timeout for server-side streaming… | `stream.timebox_ms` default is 30000 ms… | Correct timeout value retrieved and stated |
| `qst_0022` | What is the name of the Slack channel for… | Channel name from gold | Model reproduced channel name |
| `qst_0033` | Who is the DRI for… | Person name from gold | Model matched person name |

Full per-question gold vs model answers:  
`data/evals/benchmark-v1/checkpoints/full-v1-100/answers_report.jsonl`

Correct question IDs:

```
qst_0018, qst_0022, qst_0033, qst_0035, qst_0036, qst_0037, qst_0040,
qst_0043, qst_0047, qst_0054, qst_0067, qst_0078, qst_0094
```

### Incorrect but retrieved gold docs (recall=1.0, answer wrong)

Common pattern: **retrieval succeeded, generation paraphrase failed scoring**.

| ID | Doc recall | Issue |
|---|---|---|
| `qst_0001` | 1.0 | Retrieved correct docs; answer paraphrased upload limits differently than gold wording |
| `qst_0002` | 1.0 | Correct metric name but formatting/punctuation mismatch vs gold |
| `qst_0005` | 1.0 | Substantively similar failover sequence; scorer did not match |

~**40 questions** had full gold-doc recall but wrong final answer text.

### Retrieval failures (46 questions, recall=0.0)

BM25 did not retrieve any expected `dsid_*` in top-5 for **46 / 100** questions.

Examples: `qst_0004`, `qst_0006`, `qst_0007`, `qst_0010`, `qst_0013`, …

These are pure retrieval misses on the 512K corpus — answer model cannot succeed without gold docs in context.

### Error (1 question)

| ID | Error |
|---|---|
| `qst_0065` | Infrastructure/API error during run (record preserved with error field) |

---

## Context and latency (100 questions)

| Metric | Value |
|---|---|
| Context tokens (median) | **1,226** |
| Context tokens (mean) | 1,273 |
| Total latency (median) | **378 s (~6.3 min)** |
| BM25 retrieval (median) | **372 s (~6.2 min)** |
| LLM generation (median) | **3.0 s** |

**Diagnosis:** Runtime is dominated by `BM25Okapi.get_scores()` over all 511,962 documents per question — not LLM inference. See `docs/benchmark-v1-checkpoint-100-diagnosis.md`.

---

## Artifacts (immutable checkpoint)

```
data/evals/benchmark-v1/checkpoints/full-v1-100/
  bm25/results.jsonl              # 100 raw result rows
  answers_report.jsonl            # gold vs model per question (review-friendly)
  analysis_summary.json           # aggregate scores
  profile_100.json                # latency profile
  checkpoint_metadata.json        # config + integrity
  checkpoint_sha256.json          # checksums
  raw-backup-run-dir/             # 101-row backup at stop time
```

**Resumable live run** (do not delete):

```
data/evals/benchmark-v1/full-v1/runs/full-v1-baseline-001/bm25/results.jsonl
  → 101 rows (qst_0001–qst_0101); resume continues at qst_0102
```

---

## What this does NOT tell us yet

- No Dense, Hybrid, or GraphContinuum numbers (not run)
- No category diversity beyond `basic` (first 100 official questions)
- No final 500-question benchmark claim
- No graph coverage / sparse-claim diagnostics (Continuum leg pending)

---

## Recommended next steps (for founder decision)

1. **Fix BM25 retrieval performance** — full-corpus `get_scores()` per query (~6 min/q); optimize without changing top-k semantics
2. **Validate optimization** on checkpoint 100 — answers/recall unchanged, latency down
3. **Resume BM25** Q102–Q500 with checkpoint/resume
4. **Run remaining systems** (Dense, Hybrid, GraphContinuum) with same protocol
5. **Only then** publish official 500-question comparison

---

## Reproducibility

| Field | Value |
|---|---|
| Branch | `run/enterpriserag-v1-baseline` |
| Commit at checkpoint | `1340de98472428e8ad689ce9bbcf07ba54a8a96e` |
| Run ID | `full-v1-baseline-001` |
| Dataset | EnterpriseRAG-Bench v1.0.0 |
| Corpus SHA256 | `9d1174928696ad08bc15f3f104739519de633c1605a4ec2034e0e3c0087bc5cd` |
