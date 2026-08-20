# Benchmark ER v1 — Before / After Comparison

## Before (retrieval-only baseline)

Run: `subset-20pct-baseline-001`  
Mode: `--no-graph` (BM25 corpus retrieval + Fireworks answer)

| Metric | Value |
|--------|------:|
| Answer correctness | 8.75% |
| Document recall | 37.88% |
| Classified ER failures | 64 |
| Latency p50 | 17.8s |

## After (graph + ER resolver v1)

Run: `subset-20pct-er-v1-dev-001`  
Mode: graph enabled (`GraphContinuumSystem` + `EntityStore.resolve_mention` improvements)

| Metric | Before | After |
|--------|-------:|------:|
| Answer % | 8.75 | _pending run_ |
| Doc recall | 37.88 | _pending run_ |
| ER failures | 64 | _pending run_ |
| Latency p50 | 17.8s | _pending run_ |

**Run:** `make benchmark-subset-er-dev` (requires HydraDB on port 7688 + graph seed)

**Status (2026-08-20):** Graph re-run pending — Docker/HydraDB not available locally. Makefile targets and resolver changes are ready; run when `continuum-hydradb` is up on 7688.

## Resolver changes (Phase 2)

- [`continuum/entities/store.py`](../continuum/entities/store.py): case-insensitive alias match, slug normalization (`cedar-bank` ↔ `Cedar Bank`), candidate-index lookup with inventory signals
- [`continuum/entities/candidates.py`](../continuum/entities/candidates.py): `normalize_slug`, `signals_from_mention`
- Tests: [`tests/eval/test_benchmark_er_store_resolve.py`](../tests/eval/test_benchmark_er_store_resolve.py) + existing hardening suite (0 false merges)

## Failure clusters (Phase 1)

See [`benchmark-er-v1-failure-clusters.md`](benchmark-er-v1-failure-clusters.md).

Top patterns covering ≥80%: **project_names**, **multi_entity_ambiguity**, **company_alias**, **temporal_owner**.

44/72 failures had retrieval miss; 28 had retrieval OK but wrong answer.
