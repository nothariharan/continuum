# Benchmark ER v1 — Holdout Validation

Holdout set: 20 questions in `data/evals/benchmark-v1/subset-20pct/samples/sample_holdout.json`

**Rule:** Run once after dev improvement; never tune on holdout IDs.

## Status: SKIPPED

Holdout was **not run** because dev success gates were not met:

| Gate | Target | Dev result |
|------|--------|------------|
| Answer accuracy | > 8.75% | 3.75% |
| ER failures | materially ↓ vs 64 | 76 (↑) |
| False merges | 0 | 0 (tests pass) |

## Planned command (when dev improves)

```bash
make benchmark-subset-er-holdout
# run-id: subset-20pct-er-v1-holdout-001 — single run only
```

## Baseline holdout

Not run in experiment branch (dev-only baseline established first).

| Metric | Dev before | Dev after (graph) | Holdout 20Q |
|--------|----------:|------------------:|------------:|
| Answer % | 8.75 | 3.75 | _skipped_ |
| Doc recall | 37.88 | 0.0 | _skipped_ |

Document overfit if holdout does not improve when dev improves.
