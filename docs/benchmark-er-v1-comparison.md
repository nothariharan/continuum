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
| Graph state hit rate | 0.0 (graph disabled) |

## After (graph + ER resolver v1)

Run: `subset-20pct-er-v1-dev-001`  
Mode: graph enabled (`GraphContinuumSystem` + `EntityStore.resolve_mention` improvements)  
HydraDB: port 7688, Phase 2B fixture (360 artifacts, 10 claims, 16 entities)

| Metric | Before | After |
|--------|-------:|------:|
| Answer % | 8.75 | **3.75** |
| Doc recall | 37.88 | **0.0** |
| ER failures (classifier) | 64 | **76** |
| Latency p50 | 17.8s | **0.89s** |
| Graph state hit rate | — | **0.0** |
| Graph abstain rate | — | **100%** |

**Run:** `make benchmark-subset-er-dev` (HydraDB on 7688 + graph seed)

**Status (2026-08-20):** Graph dev run completed. **Success gate not met** (answer accuracy regressed). Holdout not run.

## Interpretation

This is the first apples-to-oranges Continuum path comparison:

- **Before** uses [`ContinuumSystem`](../continuum/eval/benchmark/systems/continuum.py): full-v1 BM25 retrieval + Fireworks.
- **After** uses [`GraphContinuumSystem`](../continuum/benchmark/graph_system.py): layered pipeline (entity → state → answer) **without** full corpus BM25.

Observed regressions are expected given current integration gaps:

1. **No corpus retrieval in graph path** — `retrieval_ms` ≈ 0 in aggregate; gold docs never retrieved (`doc recall 0%`).
2. **Small graph fixture** — 16 canonical entities / 10 claims vs 512K-document benchmark; `graph_state_hit_rate = 0%`.
3. **Pipeline mention extraction** — graph path resolves surface tokens like `"March"` / `"UI"` instead of benchmark entity names (outside resolver scope).

Resolver-only improvements (slug, company suffix, inventory normalization) remain valuable for entity lookup when correct mentions reach `EntityStore`, but cannot fix retrieval absence or pipeline mention extraction.

## Resolver changes (Phase 2)

- [`continuum/entities/store.py`](../continuum/entities/store.py): case-insensitive alias match, slug/company normalization, inventory index by normalized/slug keys, candidate-index lookup
- [`continuum/entities/candidates.py`](../continuum/entities/candidates.py): `normalize_slug`, `normalize_company_name`, slug/company-slug inverted indexes
- Tests: [`tests/eval/test_benchmark_er_store_resolve.py`](../tests/eval/test_benchmark_er_store_resolve.py) + hardening suite (**0 false merges**)

## Failure clusters

- Baseline (no-graph): [`benchmark-er-v1-failure-clusters.md`](benchmark-er-v1-failure-clusters.md)
- Graph run: [`benchmark-er-v1-failure-clusters-graph.md`](benchmark-er-v1-failure-clusters-graph.md)

Top patterns (both runs): **project_names**, **multi_entity_ambiguity**, **company_alias**.

## Next step (out of scope for this PR)

Combine BM25 retrieval with graph state in one Continuum adapter (retrieval → entity resolution → HydraDB state) without changing benchmark protocol or scorer.
