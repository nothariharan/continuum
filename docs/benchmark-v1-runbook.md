# Full-v1 Baseline Runbook

Branch: `run/enterpriserag-v1-baseline`  
Frozen master SHA at start: `514d5fe70fef395d3df56cd1790f91c976958a0f`

## Completed checkpoints

| Checkpoint | Status |
|---|---|
| A — master preflight | Done (benchmark tests green) |
| B — corpus verified | Done (511,963 docs, SHA256 verified) |
| B — 500 questions verified | Done (`full-v1-question-manifest.json`) |
| GraphContinuum wiring | Done (`GraphContinuumSystem` + `--with-graph`) |

## Prerequisites

1. **Docker** running for HydraDB (GraphContinuum):
   ```bash
   make hydradb-up   # or scripts/start_hydradb.ps1 on Windows
   ```
2. **LLM API key** in `.env` (`FIREWORKS_API_KEY` or `OPENAI_API_KEY`)
3. **~16GB+ RAM** for full-corpus BM25; dense/hybrid need more
4. **NumPy ≥2.0** for dense/hybrid (upgraded in venv during this run)

## Commands

```bash
# Verify corpus (already done; re-run if needed)
make benchmark-full-v1-verify

# 10-question full-corpus smoke (Checkpoint C)
PYTHONPATH=. python scripts/run_full_v1_baseline.py \
  --run-id full-v1-smoke-001 --regression --answer-model real \
  --with-graph --fail-on-fallback

# Record freeze commit SHA in run_manifest.json, then:

# Official baseline — one system at a time
PYTHONPATH=. python scripts/run_full_v1_baseline.py \
  --run-id full-v1-baseline-001 --system bm25 --answer-model real \
  --no-graph --fail-on-fallback

PYTHONPATH=. python scripts/run_full_v1_baseline.py \
  --run-id full-v1-baseline-001 --system dense --answer-model real \
  --no-graph --fail-on-fallback

PYTHONPATH=. python scripts/run_full_v1_baseline.py \
  --run-id full-v1-baseline-001 --system hybrid --answer-model real \
  --no-graph --fail-on-fallback

PYTHONPATH=. python scripts/run_full_v1_baseline.py \
  --run-id full-v1-baseline-001 --system continuum --answer-model real \
  --with-graph --fail-on-fallback

# Analysis
make analyze-full-v1-baseline
```

Runs are **resumable** — completed `question_id`s in `results.jsonl` are skipped.

## Output layout

```
data/evals/benchmark-v1/full-v1/runs/full-v1-baseline-001/
  run_manifest.json
  bm25/results.jsonl
  dense/results.jsonl
  hybrid/results.jsonl
  continuum/results.jsonl
  comparison.json
  full-v1-failure-analysis.json
```

## Graph coverage reporting

Continuum rows include `graph_coverage` with `graph_state_hit`, `claims_used_count`, and `graph_abstain`. Sparse coverage (~10 real claims) is expected and must be reported honestly in `docs/benchmark-v1-analysis.md`.

## Do not

- Modify code mid-run after smoke freeze
- Expand claims or alter the 500-question set
- Commit `data/raw/.../all_documents.zip`
