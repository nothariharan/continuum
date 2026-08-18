# Post-Stabilization Health Baseline

Status: **BATCH 0 gate** — run after every merge to master before starting new work.

## Record

| Field | Value |
|-------|-------|
| Master SHA | run `git rev-parse HEAD` |
| Recorded at | see `data/metadata/post_stabilization_baseline.json` |

## Commands

```bash
# Automated health snapshot (non-hydradb tests)
PYTHONPATH=. python3 scripts/post_stabilization_health_check.py

# Source tests
make test-sources

# Query core (no HydraDB)
PYTHONPATH=. python3 -m pytest tests/phase2b/test_query_core.py -q

# Full E2E gold set (requires HydraDB + seeded graph)
PYTHONPATH=. python3 scripts/benchmark_e2e_questions.py

# Verify benchmark checkpoints unchanged
ls data/evals/benchmark-v1/checkpoints/full-v1-100/checkpoint_sha256.json
```

## Stop conditions

Do **not** proceed to BATCH B if:

- source or query_core tests fail
- benchmark checkpoint files change unintentionally
- gold-set score regresses vs prior baseline

## Gold set

20 questions in [`data/labels/eval-questions.jsonl`](../data/labels/eval-questions.jsonl).

Target: **20/20** (founder BATCH A — query decomposition gaps).

Teammate proceeds with ingestion/sync/bot work in parallel; re-run gold set after founder merges query fixes.
