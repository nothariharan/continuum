# Phase: Source → Answer End-to-End Vertical

**Branch:** `feature/source-extraction-e2e`  
**Status:** Proven on Slack/Gmail fixtures (fixtures-only; no live connectors)

> Automatic source artifact → claim extraction → entity resolution →
> temporal/conflict state → Graph/HydraDB → QueryContext → Fireworks
> answer + provenance is proven end-to-end on Slack/Gmail fixtures.

---

## What this milestone proves

A real Slack/Gmail conversation path through Continuum:

```
Slack/Gmail fixture JSON
  → normalize → Artifact
  → participant entity resolution → resolutions lexicon
  → v2 deterministic extraction + handoff patterns
  → optional Fireworks predicate refinement (ambiguous tail only)
  → checkpoint gate (invalid LLM output cannot enter graph)
  → load_claims → HydraDB
  → EntityStore
  → answer() → temporal / conflict / provenance
  → optional RealAnswerModel (Fireworks) final text
```

**Not claimed:**

- Live Slack/Gmail API integration
- Full 500-question benchmark improvement
- Frontier model superiority
- MCP / UI

---

## Gold fixture

Cross-source gold package: [`data/ground_truth/source-e2e-v1/`](../data/ground_truth/source-e2e-v1/)

| File | Purpose |
|---|---|
| `manifest.json` | Fixture list, commit SHA, Fireworks budget cap (20) |
| `artifacts.jsonl` | 10 normalized Slack/Gmail artifacts |
| `claims.jsonl` | Hand-verified expected claims (evaluation only) |
| `resolutions.json` | Expected entity merges |
| `questions.jsonl` | 20-question gold set |
| `mentions.jsonl` | Expected mention inventory |

Source fixtures: [`data/fixtures/sources/e2e/`](../data/fixtures/sources/e2e/) plus selected files from `slack/` and `gmail/`.

Rebuild gold:

```bash
make build-source-e2e-gold
```

---

## Commands

### CI-safe (zero Fireworks calls)

```bash
make source-e2e
# or
PYTHONPATH=. python3 scripts/source_to_answer_e2e.py --refinement mock
```

### Live Fireworks smoke (≤20 calls, requires `FIREWORKS_API_KEY`)

```bash
make source-e2e-fireworks-smoke
```

Reports written to `data/metadata/`:

- `source_e2e_extraction_report.json`
- `source_e2e_fireworks_smoke.json`
- `source_e2e_latency.json`
- `source_e2e_failure_taxonomy.json`

---

## Architecture

### Robustness

| Property | Mechanism |
|---|---|
| Invalid LLM output cannot corrupt graph | `validate_refinement()` → ABSTAIN; `classify_claim()` gate before `load_claims` |
| API timeout cannot corrupt graph | `FireworksPredicateProvider` catches exceptions → ABSTAIN |
| Deterministic fallback | `create_refinement_provider("auto")` → `MockPredicateProvider` without API key |

### Performance

| Stage | LLM? |
|---|---|
| Ingest / entity resolution | No |
| v2 deterministic extraction | No |
| Predicate refinement | Fireworks **only** on `metadata.ambiguous` claims |
| State / conflict / temporal | No |
| Final answer | Fireworks **only** when `--fireworks-answer` |

Call count and per-stage latency recorded in reports.

---

## Tests

```bash
# Unit (no HydraDB)
PYTHONPATH=. pytest tests/pipeline/test_source_e2e_unit.py tests/sources/test_source_extraction_e2e.py -q -k "not hydradb and not fireworks"

# HydraDB integration (requires running HydraDB)
PYTHONPATH=. pytest tests/sources/test_source_extraction_e2e.py -m hydradb -q

# Fireworks smoke (optional, budget capped)
PYTHONPATH=. pytest tests/sources/test_source_extraction_e2e.py -m fireworks -q
```

---

## Stop condition

When this vertical is green: **STOP.**

Do not automatically:

- Add another connector
- Resume the 500-question benchmark
- Add MCP or UI

Return to founder:

- Commit SHA
- Test counts
- Extraction precision/recall vs gold
- Fireworks call count + latency
- 20-question gold-set results
- Remaining blockers (compound questions, sparse graph retrieval stub, etc.)

---

## Remaining blockers

1. **Retrieval stub** — pipeline answers from loaded claims, not BM25 over ingested corpus
2. **Query decomposition gaps** — cross-source/provenance phrasings (see `docs/phase-source-to-answer-e2e-report.md` §6)
3. **HydraDB local** — integration tests skip when Docker/HydraDB not running
4. **Entity resolution** — signal-driven key derivation is in place and deterministic; full automatic clustering (fuzzy matching, cross-org guards) is Phase 3

> Stabilization history: B1–B4 fixes (extraction quality, temporal
> validity, whitelist-free entity resolution, hermetic HydraDB lifecycle)
> are documented with before/after evidence in
> `docs/phase-source-to-answer-e2e-report.md`.
