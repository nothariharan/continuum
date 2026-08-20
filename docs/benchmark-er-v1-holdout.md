# Benchmark ER v1 — Holdout Validation

Holdout set: 20 questions in `data/evals/benchmark-v1/subset-20pct/samples/sample_holdout.json`

**Rule:** Run once after dev improvement; never tune on holdout IDs.

## Baseline holdout

Not run in experiment branch (dev-only baseline established first).

## ER v1 holdout

Run: `subset-20pct-er-v1-holdout-001`  
Command: `make benchmark-subset-er-holdout`

| Metric | Dev (80Q) before | Dev after | Holdout 20Q |
|--------|----------------:|----------:|------------:|
| Answer % | 8.75 | _pending_ | _pending_ |
| Doc recall | 37.88 | _pending_ | _pending_ |

Document overfit if holdout does not improve when dev improves.
