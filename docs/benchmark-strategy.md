# Benchmark Strategy — Continuum vs Conventional RAG

Status: **superseded for execution** by [`benchmark-protocol-v1.md`](benchmark-protocol-v1.md).
This document retains category rationale and thesis framing. The structured
Continuum question bank (`data/labels/eval-questions.jsonl`) remains the
diagnostic overlay; official ER-Bench comparisons use the protocol v1 harness.

## 1. The claim to prove

> RAG tells you what the company said. Continuum tells you what the company
> currently knows, what used to be true, what changed, what conflicts, and
> why.

The benchmark must demonstrate that the graph/state path beats retrieval
baselines specifically on questions where **state** matters (temporal,
conflict, abstention, provenance) — not on generic fact recall.

## 2. Question categories (`data/labels/eval-questions.jsonl`)

| category | count | what it tests |
|---|---|---|
| single-hop | 5 | direct state lookup (OWNS/MAINTAINS/LEADS/DEPENDS_ON/ASSIGNED_TO) |
| multi-hop | 3 | provenance chains, co-occurrence |
| temporal | 3 | as-of semantics, temporal abstention |
| conflict | 2 | conflict surfacing vs silent guessing |
| abstention | 2 | correct abstention vs hallucinated answers |
| provenance | 2 | evidence traceability |
| entity-resolution | 3 | identity pairs from the Phase 3 eval set |

## 3. System baselines to compare

1. BM25 RAG (existing: `continuum/embed/`, Recall@5 0.75 on the sample)
2. Dense RAG (existing: 0.625 Recall@5)
3. Hybrid RRF RAG (existing: 0.75)
4. GraphRAG-style baseline (retrieval + LLM over neighborhood text) —
   to be built only for the comparison
5. Continuum (graph/state path, `continuum.query`)

## 4. Model sweep (later, behind the swappable provider interface)

- small local model + raw documents
- small local model + naive retrieval
- small local model + hybrid retrieval
- small local model + Continuum structured context
- strong model + Continuum structured context

Hypothesis to measure: how much model capability can Continuum replace with
better context and state representation?

## 5. Metrics per category

| category | primary metric |
|---|---|
| single-hop | exact-answer accuracy |
| temporal | as-of correctness; abstain-on-unknown correctness |
| conflict | conflict-detection rate; never-guess rate |
| abstention | abstain precision (correct abstention / abstentions) |
| provenance | trace completeness (claim -> artifact -> source) |
| entity-resolution | same/different/uncertain accuracy, false-merge rate (Phase 3 set) |
| all | p50/p95/p99 latency, nodes touched, edges traversed |

## 6. Harness rules

- The same question set runs against every baseline; no per-baseline
  question cherry-picking.
- Latency numbers from the existing `eval_*`/`benchmark_*` scripts only
  when the graph is the same fixture (deterministic loads).
- Abstention is scored as correct only when the system says "unknown" —
  a wrong guess never counts as a partial credit.
- Results are committed as JSON under `data/metadata/` with the fixture id
  recorded (synthetic / real sample / full benchmark).

## 7. When this runs

1. Teammate delivers graph-loadable claims (Gate 2 pass)
2. Contract stays v1; the harness `--fixture` parameter already covers
   synthetic / real-sample runs without core changes
3. Entity resolution exists (Phase 3) so entity-resolution questions
   resolve against canonical entities
