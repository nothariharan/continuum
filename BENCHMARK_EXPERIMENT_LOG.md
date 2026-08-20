# Benchmark 20% Subset — Experiment Log

Branch: `experiment/benchmark-20pct`  
Sample: 100Q proportional (seed 42), dev 80 / holdout 20

---

## BASELINE (Stage 2a — mock harness, sample-v1)

**Run ID:** `subset-20pct-mock-001`  
**Corpus:** sample-v1 (360 docs, dev-only)  
**System:** continuum, mock answer model, `--no-graph`

| Metric | Value |
|--------|------:|
| Questions | 100 |
| Answer correctness | 0.0 |
| Document recall mean | 0.0053 |
| Correct / incorrect | 0 / 100 |

**Category balance:** matches manifest (35 basic, 25 semantic, …).  
**Note:** Expected low scores on sample-v1 — ~1 gold-doc overlap in 100Q subset.

**Decision:** BASELINE FROZEN (harness validation passed; not publishable per protocol)

---

## BASELINE (Stage 2b — real dev 80Q, full-v1 corpus)

**Run ID:** `subset-20pct-baseline-001`  
**Status:** pending full corpus download + Fireworks run  
**Command:** `make benchmark-subset-baseline`

---

## Experiments

No tuning experiments yet. Failure analysis (mock + real baseline) must complete before Phase 4 single-change loop.

### EXP-01 (reserved)

Hypothesis: _TBD from failure taxonomy_  
Decision: _pending_

---

## Holdout validation

Not run. Holdout 20Q (`sample_holdout.json`) runs only after a KEEP decision on dev 80Q.
