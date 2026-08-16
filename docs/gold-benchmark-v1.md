# Gold Benchmark v1 — Data Evaluation

Status: **active** on branch `feature/data-evaluation`.

## Purpose

Provide a reproducible 150-artifact gold set and versioned extraction evaluation runs for the current V2 extraction pipeline (deterministic + optional Fireworks hybrid). This is evaluation metadata only — it does **not** change contract v1 extraction outputs.

## Layout

```
data/ground_truth/v1/
  manifest.json
  artifacts.jsonl      # 150 artifacts from phase2a-sample
  mentions.jsonl         # gold mention labels
  claims.jsonl           # gold claim labels (status: VALID | AMBIGUOUS)
  ambiguities.jsonl      # NO_CLAIM / AMBIGUOUS artifact records

data/evals/
  run_001/               # deterministic baseline
  run_002/               # hybrid + Fireworks
  failures/              # categorized failure examples
```

## Repro commands

| command | does |
|---|---|
| `make gold-v1` | build `data/ground_truth/v1/` from sample + legacy labels |
| `make enrich-gold-claims` | seed VALID claims from `phase2b_real_claims.jsonl` |
| `make eval-run RUN=001 STRATEGY=deterministic` | write `data/evals/run_001/` |
| `make eval-run RUN=002 STRATEGY=hybrid` | hybrid eval (requires `FIREWORKS_API_KEY`) |
| `make test-eval` | run gold/eval unit tests |

Before every push: `python -m pytest tests -q -m "not hydradb"`

## Gold claim status semantics

| status | scoring |
|---|---|
| `VALID` | included in strict P/R; missed predictions are FN |
| `NO_CLAIM` | abstention rewarded when pipeline emits zero claims |
| `AMBIGUOUS` | excluded from strict abstention score |

## Experiment metadata (each run)

Every run records: dataset version, commit SHA, model, prompt version, strategy, runtime, memory peak, model calls (hybrid), mention/claim metrics, failure summary, and a suggested next step for the system owner.

## Out of scope

- Entity resolution / merge decisions
- HydraDB graph loading at scale
- Changes to `continuum/hydradb/`, `continuum/query/`, `continuum/state/`

## Next phases (not this PR)

- Scaling slices (360 → 1k → …)
- Identity candidate features (`data/entity_resolution/`)
- Retrieval benchmark unification with `eval-questions.jsonl`
