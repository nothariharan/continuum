# Identity-Pair Gold Dataset v1

Evaluation artifact for Phase 3 entity resolution. This dataset is **data/eval
owned** — it does not modify `continuum/entities/resolver.py` or scoring
thresholds.

## Layout

```
data/entity_resolution/v1/
  identity-pairs-schema.json     JSON Schema for one labeled pair row
  identity-pairs.jsonl           75–150 gold pairs + FeatureVector features
  identity_pairs_report.json     label distribution + feature coverage
```

## Labels

| Legacy (`phase3-identity-pairs.jsonl`) | Canonical |
|---|---|
| `same` | `SAME_ENTITY` |
| `different` | `DIFFERENT_ENTITY` |
| `uncertain` | `UNCERTAIN` |

## Feature slots

Layer 1 (from `continuum.entities.scoring.compute_features`):

- `name_similarity`, `email_match`, `email_username_match`, `username_match`,
  `external_id_match`, `source_overlap`

Layer 2 (teammate extensions via artifact join):

- `cooccurrence` — Jaccard overlap of inventory `artifact_ids`
- `shared_project` — shared SUP/ENG/INC ticket keys from artifact text
- `shared_repository` — shared GitHub repo paths from artifact metadata/content
- `shared_channel` — shared Slack channel names from artifact titles
- `embedding_similarity` — optional; `null` when built with `--no-embed` (default)

`null` means no evidence, not zero.

## Regenerate

```bash
make identity-pairs-v1
make test-identity-data
```

Or step-by-step:

```bash
python scripts/build_identity_pairs_v1.py
python scripts/generate_identity_features.py
python scripts/eval_identity_pairs.py
```

Optional embeddings:

```bash
python scripts/generate_identity_features.py --embed
```

## Founder next step

Wire `data/entity_resolution/v1/identity-pairs.jsonl` into the resolver eval
harness and tune the REVIEW threshold on the UNCERTAIN tail. Import
`compute_features` / `FeatureVector` from `continuum.entities` — do not fork
scoring rules on the data side.

Legacy path `data/labels/phase3-identity-pairs.jsonl` remains for backward
compatibility; `make identity-pairs` still runs the Phase 3 builder.
