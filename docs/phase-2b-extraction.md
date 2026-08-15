# Phase 2B — Mention/Claim Extraction Pipeline

Status: **ready for PR** on branch `feature/phase2b-extraction`.

## Goal

Turn 360 real EnterpriseRAG-Bench artifacts into **contract-validated** `mentions.jsonl` and `claims.jsonl`, with a **measured extraction benchmark** on a labeled subset.

**Out of scope for this PR:** entity resolution, mention inventory merge, HydraDB/graph loading, MCP, or UI.

## Shared contract

See [contract-v1.md](contract-v1.md) for Artifact/Mention/Claim schemas and timestamp semantics.

## Repro pipeline

| command | does |
|---|---|
| `python scripts/build_ground_truth.py` | writes `data/labels/phase2b-ground-truth.jsonl` (150 artifacts) |
| `make extract-dataset` | hybrid extraction on 360 artifacts + validation report |
| `make extract-mentions` | writes `data/extraction/mentions.jsonl` (default: deterministic) |
| `make extract-claims` | writes `data/extraction/claims.jsonl` (default: deterministic) |
| `make validate-extraction` | writes `data/metadata/extraction_validation.json` |
| `make eval-extraction` | validation + `data/metadata/extraction_metrics.json` |
| `make embedding-experiment` | updates `data/metadata/embedding_experiment.json` with MRR |
| `make test-phase2b` | runs unit tests (no HydraDB required) |

`make mention-inventory` exists for a **future** entity-resolution phase and is not part of this PR.

## Modules

- `continuum/extract/` — Mention/Claim schemas, deterministic extractors, optional LLM hybrid
- `continuum/eval/` — ground-truth loading, precision/recall metrics, contract validation
- `scripts/extract_{mentions,claims}.py`, `eval_extraction.py`, `validate_extraction.py`, `build_ground_truth.py`
- `tests/phase2b/` — schema, mention, claim, eval, validation tests

## Extraction strategies

1. **Deterministic** (baseline) — source-metadata regex and header parsing
2. **Hybrid** (shipped dataset) — deterministic first, LLM gap-fill when `FIREWORKS_API_KEY` is set
3. **LLM** — LLM-only when API key set (comparison baseline)

### LLM setup (Fireworks)

Copy `.env.example` to `.env` and set the founder-provided key:

```bash
cp .env.example .env
# edit .env:
# FIREWORKS_API_KEY=fw_...
# CONTINUUM_LLM_MODEL=accounts/fireworks/models/gpt-oss-20b
pip install -e ".[test,extract,llm]"
make extract-dataset
make eval-extraction
```

Fireworks uses the OpenAI-compatible endpoint at `https://api.fireworks.ai/inference/v1`.
Override the model with `CONTINUUM_LLM_MODEL` if the founder specifies a different Fireworks model id.

Supported claim predicates: `OWNS`, `LEADS`, `ASSIGNED_TO`, `BLOCKS`, `DEPENDS_ON`, `REVIEWS`.

Minimum claim confidence threshold: **0.70**.

## Validation

`make validate-extraction` checks every committed row against contract v1:

- schema round-trip via `Mention` / `Claim` dataclasses
- `artifact_id` must be a `dsid_*` present in `phase2a-sample.jsonl`
- stable `mention_id` / `claim_id` hashes
- non-empty `evidence_span` on claims
- coverage summary (artifacts with zero extractions are expected for sparse sources)

Output: `data/metadata/extraction_validation.json`

## Checkpoint #2 deliverable

Top 50 claims by confidence for founder verification:

```bash
python scripts/extract_claims.py --method hybrid --limit 50 --out data/extraction/claims_checkpoint50.jsonl
```

Founder verifies: Artifact → Claim → HydraDB → Query → Evidence.

## Phase 2B exit criteria

- [x] Ground-truth extraction set exists (`data/labels/phase2b-ground-truth.jsonl`)
- [x] Mention schema locked (`docs/contract-v1.md`)
- [x] Claim schema locked (`docs/contract-v1.md`)
- [x] Full JSONL contract validation (`data/metadata/extraction_validation.json`)
- [x] Mention precision/recall measured (`data/metadata/extraction_metrics.json`)
- [x] Claim precision/recall measured (limited gold set — mostly BLOCKS/OWNS)
- [x] Extraction strategies compared (deterministic / hybrid)
- [x] Retrieval benchmark updated with MRR
- [x] Candidate claim JSONL reproducible (`data/extraction/claims.jsonl`)
- [x] Provenance preserved (`evidence_span`, `extraction_method` on every claim)
- [ ] Phase 1 regression remains green (founder verifies with HydraDB)
- [ ] 50-claim joint verification passes (founder checkpoint #2)

## Next (Phase 2C+)

Entity resolution (joint with founder), mention inventory merge, claims loader into HydraDB, hybrid retrieval wired to query layer.
