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

**Decision:** BASELINE FROZEN (harness validation passed; not publishable per protocol)

---

## BASELINE (Stage 2b — real dev 80Q, full-v1 corpus)

**Run ID:** `subset-20pct-baseline-001`  
**Corpus:** full-v1 (512K docs, SHA verified)  
**System:** continuum, Fireworks `gpt-oss-20b`, `--no-graph`  
**Runtime:** ~25 min (corpus load + 80Q)

| Metric | Value |
|--------|------:|
| Questions | 80 |
| Answer correctness | **0.0875** |
| Document recall mean | **0.3788** |
| Correct / incorrect / unanswered | 16 / 56 / 8 |
| Latency p50 / p95 | 17.8s / 29.9s |

**Per-category highlights:** info_not_found 1.0, conflicting_info 0.67, project_related 0.5, basic 0.16, semantic 0.1.

**Decision:** BASELINE FROZEN — official dev baseline for experiment loop.

---

## BASELINE (Stage 2c — Track B capability)

| Track | Result |
|-------|--------|
| source-e2e (mock, skip-graph) | extraction P/R 0.556 / 0.714 |
| benchmark-e2e | 3/20 (entity-resolution only; graph queries blocked — HydraDB port 7687 conflict) |

Reports: `benchmark-results/capability-baseline/`

---

## Failure taxonomy (dev 80Q real baseline)

| Failure type | Count | % of failures | Examples |
|--------------|------:|--:|----------|
| ENTITY_RESOLUTION_FAILURE | 64 | 100% | qst_0003, qst_0016, qst_0031, … |

**Top cluster:** retrieval/entity path — wrong or missing canonical entity in answer despite partial doc recall (mean 0.38).

Full table: `benchmark-results/baseline-20pct-dev-errors.md`

---

## Experiments

No KEEP/REVERT experiments executed. Plan Phase 4 requires single-change loop **after** failure review; top mode is entity/retrieval ranking (coordinate with founder for graph path).

### EXP-01 (deferred)

Hypothesis: Improve retrieval recall on semantic + basic types (BM25/hybrid diagnostic first).  
Decision: **DEFER** — graph path not enabled in baseline; enable HydraDB on isolated port before query-layer experiments.

---

## Holdout validation

Not run. Command when ready: `make benchmark-subset-holdout`
