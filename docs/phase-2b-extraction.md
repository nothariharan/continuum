# Phase 2B — Mention/Claim Extraction Pipeline

Status: **done** on branch `feature/phase2b-extraction`.

## Goal

Turn real EnterpriseRAG-Bench artifacts into mentions, candidate claims, evaluation metrics, and entity-resolution prep signals for the founder to load into HydraDB. Does **not** include graph loading, entity merge, MCP, or UI.

## Shared contract

See [contract-v1.md](contract-v1.md) for Artifact/Mention/Claim schemas and timestamp semantics.

## Repro pipeline

| command | does |
|---|---|
| `python scripts/build_ground_truth.py` | writes `data/labels/phase2b-ground-truth.jsonl` (150 artifacts) |
| `make extract-mentions` | writes `data/extraction/mentions.jsonl` |
| `make extract-claims` | writes `data/extraction/claims.jsonl` |
| `make eval-extraction` | writes `data/metadata/extraction_metrics.json` |
| `make mention-inventory` | writes `data/extraction/mention_inventory.json` |
| `make embedding-experiment` | updates `data/metadata/embedding_experiment.json` with MRR |
| `make test-phase2b` | runs unit tests (no HydraDB required) |

## Modules

- `continuum/extract/` — Mention/Claim schemas, deterministic extractors, optional LLM hybrid, inventory
- `continuum/eval/` — ground-truth loading, precision/recall metrics
- `scripts/extract_{mentions,claims}.py`, `eval_extraction.py`, `mention_inventory.py`, `build_ground_truth.py`
- `tests/phase2b/` — schema, mention, claim, eval, inventory tests

## Extraction strategies

1. **Deterministic** (primary) — source-metadata regex and header parsing
2. **Hybrid** — deterministic first, LLM gap-fill when `FIREWORKS_API_KEY` (or `OPENAI_API_KEY`) is set
3. **LLM** — LLM-only when API key set (comparison baseline)

### LLM setup (Fireworks)

Copy `.env.example` to `.env` and set the founder-provided key:

```bash
cp .env.example .env
# edit .env:
# FIREWORKS_API_KEY=fw_...
# CONTINUUM_LLM_MODEL=accounts/fireworks/models/gpt-oss-20b
pip install -e ".[test,extract,llm]"
python scripts/extract_claims.py --method hybrid
python scripts/eval_extraction.py
```

Fireworks uses the OpenAI-compatible endpoint at `https://api.fireworks.ai/inference/v1`.
Override the model with `CONTINUUM_LLM_MODEL` if the founder specifies a different Fireworks model id.

Supported claim predicates: `OWNS`, `LEADS`, `ASSIGNED_TO`, `BLOCKS`, `DEPENDS_ON`, `REVIEWS`.

Minimum claim confidence threshold: **0.70**.

## Checkpoint #2 deliverable

Top 50 claims by confidence for founder verification:

```bash
python scripts/extract_claims.py --limit 50 --out data/extraction/claims_checkpoint50.jsonl
```

Founder verifies: Artifact → Claim → HydraDB → Query → Evidence.

## Phase 2B exit criteria

- [x] Ground-truth extraction set exists (`data/labels/phase2b-ground-truth.jsonl`)
- [x] Mention schema locked (`docs/contract-v1.md`)
- [x] Claim schema locked (`docs/contract-v1.md`)
- [x] Mention precision/recall measured (`data/metadata/extraction_metrics.json`)
- [x] Claim precision/recall measured
- [x] Extraction strategies compared (deterministic / hybrid / llm)
- [x] Retrieval benchmark updated with MRR
- [x] Candidate claim JSONL reproducible (`data/extraction/claims.jsonl`)
- [x] Provenance preserved (`evidence_span`, `extraction_method` on every claim)
- [ ] Phase 1 regression remains green (founder verifies with HydraDB)
- [ ] 50-claim joint verification passes (founder checkpoint #2)

## Next (Phase 2C+)

Entity resolution (joint with founder), claims loader into HydraDB, hybrid retrieval wired to query layer.
