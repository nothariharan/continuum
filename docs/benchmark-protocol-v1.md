# Benchmark Protocol v1

Status: **active constitution** for Continuum vs RAG comparisons. Execution harness:
`make benchmark-foundation` (dev) and `make benchmark-foundation-official` (official).

Supersedes the narrative in [`benchmark-strategy.md`](benchmark-strategy.md) for runnable comparisons.

## Fairness rule

> All systems must receive the **same questions**, the **same corpus**, and as much of the **same answer-generation setup** as practical.

Every run records `corpus_mode`, `answer_model`, `top_k`, temperature, timeout, and context budget in the manifest and reports.

## Dataset

| Field | Value |
|---|---|
| Dataset | EnterpriseRAG-Bench |
| Version | v1.0.0 |
| Manifest pin | `continuum/dataset/manifest_v1.0.0.json` |
| Official questions | release `questions.jsonl` (500 rows) |
| Question metadata | use official `question_type` as-is |

Official `question_type` values include: `basic`, `semantic`, `intra_document_reasoning`, `project_related`, `constrained`, `conflicting_info`, `completeness`, `miscellaneous`, `high_level`, `info_not_found`.

## Corpus modes (do not conflate)

| Mode | Purpose | Corpus | Questions | Official benchmark? |
|---|---|---|---|---|
| `sample-v1` | Development, CI, regression, trace | `data/samples/phase2a-sample.jsonl` (360 docs) | Stratified dev slice (~75) | **No** |
| `full-v1` | Official benchmark | `data/raw/.../all_documents.zip` (~512K docs) | Full official `questions.jsonl` (500) | **Yes** |

**Never publish `sample-v1` results as the official benchmark.**

Only ~7 official questions have gold `expected_doc_ids` inside the 360-doc sample. Sample-mode scores measure harness plumbing, not final benchmark performance.

## Question sets

Artifacts live under `data/evals/benchmark-v1/`:

```
sample-v1/manifest.json
sample-v1/questions.jsonl
sample-v1/regression/questions.jsonl   # ~10 hardest dev/regression rows
full-v1/manifest.json
full-v1/questions.jsonl                # all 500 official questions
```

Builder: `python scripts/build_benchmark_v1.py --mode {sample-v1|full-v1|all}`

## Reference handling

Each official row includes:

- `gold_answer` — primary reference string
- `answer_facts` — atomic fact strings
- `expected_doc_ids` — gold document IDs (`dsid_*`)

Abstention/not-found: when gold answer indicates missing information, a correct system must not invent an answer. Mock mode uses deterministic stubs; real mode uses the shared prompt below.

## Retrieval corpus

- **sample-v1:** normalized JSONL sample (deterministic seed `20260815`, 40 docs/source)
- **full-v1:** SHA-verified `all_documents.zip` via `continuum.dataset.download`

Artifact text format for retrieval: `"{title}\n{content}"`.

## Shared answer generation

| Parameter | Default |
|---|---|
| Prompt template | see `continuum/eval/benchmark/answer_mock.py` (`ANSWER_PROMPT`) |
| Mock model | `mock-v1` (deterministic, no API) |
| Real model | single env-configured model (`FIREWORKS_API_KEY` or `OPENAI_API_KEY`) |
| Temperature | `0.0` |
| Timeout | `30s` |
| Context char budget | `12000` |

**Do not change the generation model per system** in v1 comparisons.

## Top-k

Default `top_k = 5` for BM25, Dense, Hybrid, and Continuum retrieval step (manifest-locked).

## Systems compared

1. BM25 RAG
2. Dense embedding RAG
3. Hybrid RRF RAG
4. Continuum (hybrid retrieval + structured state context; graph stage optional via `--with-graph`)

Baselines share: question → retrieve top-k → shared prompt → answer model.

Continuum additionally records: `resolved_entities`, `claims_used`, `state_result`, `conflicts`, `evidence`.

## Latency measurement

Per result row:

```text
latency_breakdown.retrieval_ms
latency_breakdown.entity_ms
latency_breakdown.graph_ms
latency_breakdown.state_ms
latency_breakdown.generation_ms
latency_ms (total)
```

## Context efficiency

Per result row:

```text
retrieved_artifacts (count via list length)
context_chars
context_tokens
evidence_items
```

Compare especially **Continuum context tokens vs Hybrid context tokens**.

## Scoring

### OFFICIAL SCORE (benchmark-native)

Kept separate from internal diagnostics:

- `answer_correctness`
- `document_recall_mean` (retrieved IDs vs `expected_doc_ids`)
- `invalid_extra_evidence_mean`

### CONTINUUM DIAGNOSTICS

Structured graph/state checks from `data/labels/eval-questions.jsonl` and `scripts/benchmark_e2e_questions.py` — **not** substituted for official ER-Bench score.

## Errors

Recorded per row when applicable:

- retrieval timeout / empty retrieval
- graph abstain (`unknown - abstain`)
- generation timeout
- invalid extra evidence (retrieved docs outside gold set)

## Commands

```bash
make build-benchmark-v1
make benchmark-foundation              # sample-v1, mock
make benchmark-foundation-official     # full-v1, real model (requires corpus download + API key)
make benchmark-trace QUESTION=qst_0001
make test-benchmark
```

## Joint review checklist

Before treating results as comparable, both teammates agree on:

- [ ] same corpus mode
- [ ] same question set version
- [ ] same answer model + temperature
- [ ] same top-k
- [ ] same context budget measurement
- [ ] same scoring block (`official_score` vs `continuum_diagnostics`)
- [ ] same timeout policy

## Founder next step

Consume `reports/full-v1/comparison.json` to tune Continuum entity/graph/state packaging without changing baseline retrieval fairness.
