# Benchmark v1 — 100-Question BM25 Baseline Insights

**Status:** FULL-V1 PARTIAL CHECKPOINT — 100/500
**Lineage:** `master @ 514d5fe` → PR #8 → `full-v1-baseline-001` → immutable `full-v1-100`
**Scope:** This is an analysis of the existing checkpoint. It does NOT modify the checkpoint, the corpus, the question set, scoring, or the benchmark protocol.

---

## 1. What exactly was benchmarked?

| Field | Value |
|---|---|
| Corpus | EnterpriseRAG-Bench v1.0.0 `all_documents.zip` — **511,962** `.txt` documents (+1 `questions.jsonl` in the zip) |
| Corpus SHA256 | `9d1174928696ad08bc15f3f104739519de633c1605a4ec2034e0e3c0087bc5cd` — **verified locally against the actual zip on disk** |
| Questions | First **100 / 500** official questions, in official order (`qst_0001`–`qst_0100`) |
| Question type | All 100 are `basic` |
| System | BM25 (leg 1 of 4). Dense / Hybrid / GraphContinuum were **not** run. |
| Answer model | `accounts/fireworks/models/gpt-oss-20b`, temperature 0.0, top_k 5, context budget 12,000 chars |
| Run ID / commit | `full-v1-baseline-001` / `1340de98472428e8ad689ce9bbcf07ba54a8a96e` |

## 2. Headline numbers

| Metric | Value | Note |
|---|---|---|
| Answer correctness (official pipeline) | **13%** (13/100) | **4 of the 13 are scoring artifacts — see §5** |
| Genuine correct answers | **9%** (9/100) | All 9 have full document recall |
| Document recall (mean) | **54%** | Recall computed over top-5 |
| Zero-recall questions | **46 / 100** | Gold doc not in top-5 |
| Retrieval-hit / answer-wrong | **45 / 100** | Gold doc retrieved but answer scored wrong |
| Infrastructure errors | 1 (`qst_0065`, connection error) | |
| Median latency / question | **378 s** | |
| Median BM25 retrieval | **373.6 s** | ~99% of total |
| Median answer generation | **3.1 s** | |
| Median context tokens | 1,226 | |

## 3. Verified independently (this review)

- Corpus SHA256 + per-source counts **match** the committed inventory and the pinned dataset manifest (511,962 `.txt`; the 511,963 inventory figure includes the zip's `questions.jsonl`).
- The 500-question set is **semantically identical** to the official `questions.jsonl` inside the corpus zip (same IDs, same order, same fields/values; only JSON key-order formatting differs).
- Checkpoint: exactly 100 rows, `qst_0001`–`qst_0100` contiguous, no duplicates; SHA256 manifest **validates against the git blobs**; 101-row raw backup is consistent; resume-by-question-id verified with an isolated temp run (no duplicates, extend-with-`--max-questions`, torn-tail resume now tolerated).
- Scoring code, BM25 code, question loader, and schema were **unchanged by PR #8** — the PR only adds orchestration/checkpointing/measurement.
- Latency profile recomputed from the raw rows matches the published profile (378 / 374 / 3.1 s medians).

## 4. Why is it slow? (BM25 diagnosis)

Confirmed at code level and consistent with the recorded per-row latency: `BM25Okapi.get_scores()` (rank-bm25) loops over **all 511,962 per-document term dicts in Python for every query term**, then `search()` performs a full Python-level sort of the 512K-element score vector. That is the entire ~6-minute cost per question. The LLM is ~3 s — **not the bottleneck**. The scaling experiment to reproduce this on this machine was intentionally stopped per direction; the code path and the checkpoint's own per-row timings are sufficient evidence.

## 5. The real failure distribution (2×2 matrix)

| | ANSWER CORRECT | ANSWER WRONG | TOTAL |
|---|---|---|---|
| **RETRIEVAL HIT** (recall > 0) | 9 | 45 | 54 |
| **RETRIEVAL MISS** (recall = 0) | 4 (all artifacts) | 42 | 46 |

### 5a. Scorer artifact: 4 of the 13 "correct" are not real correct answers

`score_answer("", gold)` returns **True** because the normalized empty string is a substring of any gold answer (`"" in gold_n`). This is a pre-existing bug in `continuum/eval/benchmark/scoring.py` (not introduced by PR #8). Four rows with **empty** model answers therefore scored "correct":

- `qst_0033` (recall 0, empty answer)
- `qst_0036` (recall 0, empty answer)
- `qst_0065` (recall 0, **connection error** — the infrastructure failure row)
- `qst_0084` (recall 0, empty answer)

**True answer correctness is 9/100 (9%), not 13%.**

### 5b. Documentation error in PR #8

The PR body and `docs/benchmark-v1-checkpoint-100-results.md` list a "correct answers (13)" ID set that **does not match the actual scorer output**. Of the 13 documented IDs, 8 actually score **False** on the checkpoint data (`qst_0037, qst_0040, qst_0043, qst_0047, qst_0054, qst_0067, qst_0078, qst_0094` — e.g. `qst_0067`'s answer is `unknown - abstain`). The true scored-correct set is `qst_0018, qst_0022, qst_0033, qst_0035, qst_0036, qst_0044, qst_0046, qst_0055, qst_0063, qst_0065, qst_0066, qst_0073, qst_0084`. The aggregate 13% is computed correctly; only the prose list is wrong.

### 5c. Retrieval hits that failed answer scoring: 45

Gold-token overlap between the model answer and the gold answer:

| Bucket | Count | Interpretation |
|---|---|---|
| 0.4–0.6 (near-miss) | 21 | Substantively correct paraphrase rejected by the ≥60%-token-overlap scorer |
| 0.2–0.4 (partial) | 20 | Partially correct; missing or restructuring content |
| < 0.2 (wrong) | 4 | Genuine generation failure / hallucination |

**The answer-scoring layer is a second bottleneck** — the lexical scorer (`score_answer` with ≥60% gold-token overlap) rejects legitimate paraphrases. ~21 of 45 hit-but-wrong answers are near-misses that a semantic/human scorer would likely accept.

### 5d. Retrieval misses: 46 — a ranking/scale problem, not vocabulary mismatch

- Gold-doc ↔ query token overlap is **high**: median 0.67; 42/46 > 0.5; 34/46 > 0.6. E.g. `qst_0004` gold doc overlaps the query at 0.97 yet was outranked by a single Drive doc at 0.74.
- Gold answers are 84% token-present in the gold docs — the answer exists in the evidence.
- Gold doc length is **not** the driver: miss gold docs median 5.9 KB vs hit gold docs 5.7 KB.
- 10/46 misses have gold-doc overlap **greater than the max retrieved doc's** overlap; 17/45 have gold overlap ≥ the retrieved average. The gold doc is often not obviously worse than what BM25 returned.

**Explanation:** on a 512K corpus of enterprise documents, lexical overlap with the query is **non-discriminative** for conversational/long-form sources. Many docs share the query's vocabulary, so the gold doc loses on BM25 term-weighting/ranking against thousands of near-ties. This is a scale + ranking problem, not a tokenizer or vocabulary problem.

Source split makes this concrete:

| Source | Retrieval outcome |
|---|---|
| **Weak (miss-heavy)** | google_drive (9 miss), slack (8 miss, 0 correct across all 11), linear (8 miss), fireflies (5 miss) |
| **Strong (hit-heavy)** | jira (11 hit), gmail (8 hit, 4 correct), github (7 hit), hubspot (4 hit, 2 correct) |

Conversational/meeting/thread content (Slack, Fireflies) and long Drive docs defeat lexical retrieval on scale; structured keyword-dense sources (Jira, Gmail, GitHub) survive it.

## 6. What this implies for Continuum

1. **Traditional BM25 RAG on this corpus is fundamentally limited by ranking, not latency.** Even a fast BM25 would still retrieve the wrong docs ~46% of the time for these `basic` questions.
2. **Conversational sources (Slack, Fireflies, Drive, Linear) are where retrieval quality collapses** — exactly the sources where a claim/entity/state graph (entity resolution + temporal state) has the most to add, and where Continuum's architecture is aimed.
3. **Answer scoring is a real second bottleneck** — lexical ≥60%-overlap scoring under-counts correct paraphrases. For Continuum comparisons, the scorer must be applied identically to all systems (fairness), but its bias must be understood when interpreting scores.
4. **The `score_answer` empty-string bug inflates correctness** — it must be fixed before any cross-system comparison, otherwise empty answers and infra errors silently add false "correct" counts. (Per review constraint, scoring was **not** modified; this is a recommendation for a team decision.)

## 7. What must remain unchanged for a fair comparison

- Corpus, question order, `top_k=5`, temperature 0.0, context budget, answer model, and the scoring function **as-is** across all four legs.
- The immutable `full-v1-100` checkpoint stays untouched; any future BM25 optimization must use a **new run ID** and prove answers/recall unchanged on the checkpoint before resuming.

## 8. Baseline limitations (explicit)

- This is a **100-question partial baseline of `basic`-type questions only**. It says nothing about the other 9 question categories (semantic, completeness, conflicting_info, constrained, project_related, etc.) that make up the other 400 questions.
- It is **not** "13% on EnterpriseRAG-Bench" — it is "BM25 on the first 100 official questions (all basic), with a scoring artifact inflating correctness from 9% to 13%."
- **GraphContinuum has NOT been benchmarked** in this checkpoint. Only the wiring exists (and was not exercised in this run).

## 9. What should we optimize / run next (decision input)

| Priority | Item | Why |
|---|---|---|
| 1 | Fix `score_answer` empty-string bug + fix the incorrect correct-ID list in the docs | Integrity of the metric before any comparison |
| 2 | Decide BM25 retrieval performance path (persistent index / pruning) only if a complete 500Q BM25 leg is needed | ~6 min/q × 400 ≈ 40 h on the same Mac; retrieval quality — not speed — is the limiting factor on this corpus |
| 3 | Resume Q101–Q500 **only after** a decision that a full BM25 baseline is worth the cost | The checkpoint already gives the strategic insight (§6) |
| 4 | Prioritize Continuum/GraphContinuum leg over burning hours on BM25 | The 100Q result isolates where lexical RAG breaks; Continuum targets those failure modes |

---

*Analysis artifacts produced during review (not part of PR #8, untracked): `data/metadata/pr8_review_miss_analysis.json`, `data/metadata/pr8_review_hitwrong_analysis.json`.*