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

### EXP-01 — EntityStore mention resolution

Hypothesis: Slug + case-insensitive alias + candidate-index lookup reduces ER failures on project/company mentions.  
Files: `continuum/entities/store.py`, `continuum/entities/candidates.py`  
Track A dev 80Q (no-graph baseline): 8.75%  
Track A dev 80Q (graph path): **3.75%** (regressed — no corpus retrieval in graph adapter)  
False merges: **0** (hardening suite green)  
Decision: **KEEP** resolver code; **do not merge** as benchmark win until retrieval+graph integration lands

---

## Holdout validation

**Skipped** — dev gates not met. See `docs/benchmark-er-v1-holdout.md`.
