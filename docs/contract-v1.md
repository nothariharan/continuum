# Contract v1 — Phase 2B Shared Data Contract

Status: **LOCKED v1** (founder sign-off complete — canonical implementation
single-sourced in `continuum/claims/schema.py`; `continuum/extract/schemas.py`
re-exports it. Graph-side mapping verified via `scripts/checkpoint_claims.py`:
the boundary is proven, extraction quality is the open blocker — see
`docs/phase-2b-claims.md`.)

This document defines the interface between the Data/ML pipeline (mention/claim extraction) and the Graph/System pipeline (HydraDB loading, state engine, queries).

## Principles

1. Extraction outputs **raw mentions**, not canonical entity IDs.
2. The founder maps `subject_mention` / `object_mention` → canonical IDs during entity resolution.
3. Open-ended validity uses `valid_to: null`; the founder converts to HydraDB sentinel `9999-12-31`.
4. Every claim must include `evidence_span` (verbatim quote) and `extraction_method`.

## Artifact (reference — unchanged from Phase 2A)

Defined in [`continuum/dataset/artifact.py`](../continuum/dataset/artifact.py):

```
id, source, source_id, type, author, timestamp, title, content, metadata
```

Real artifacts use `id = dsid_<32-hex>`.

**Live source ingestion** (Slack, Gmail, etc.) uses `Artifact.from_source_record()`
and stores the native upstream ID in `source_id`. See
[`source-ingestion-contract.md`](source-ingestion-contract.md) for the adapter
boundary and provenance metadata rules.

## Mention (Phase 2B output)

| Field | Type | Description |
|-------|------|-------------|
| `mention_id` | string | Stable hash of artifact_id + raw_text + type + span_start |
| `artifact_id` | string | Parent artifact `dsid_*` |
| `source` | string | slack \| gmail \| linear \| ... |
| `raw_text` | string | Surface form as found in artifact |
| `type` | string | person \| project \| account \| ticket \| email \| username \| org |
| `context` | string | Surrounding text (±120 chars) |
| `source_identity` | string \| null | Email, @handle, ticket key |
| `span_start` | int | Char offset in artifact.content |
| `span_end` | int | Char offset end |
| `extraction_method` | string | deterministic \| llm \| hybrid |
| `confidence` | float | 0.0–1.0 |

Output: [`data/extraction/mentions.jsonl`](../data/extraction/mentions.jsonl)

## Claim (Phase 2B output)

| Field | Type | Description |
|-------|------|-------------|
| `claim_id` | string | Stable hash of artifact_id + subject + predicate + object |
| `artifact_id` | string | Parent artifact |
| `subject_mention` | string | Raw subject (NOT canonical ID) |
| `predicate` | string | OWNS \| LEADS \| ASSIGNED_TO \| BLOCKS \| DEPENDS_ON \| REVIEWS |
| `object_mention` | string | Raw object (NOT canonical ID) |
| `observed_at` | string \| null | ISO-8601 from artifact timestamp |
| `valid_from` | string \| null | Only if explicitly stated |
| `valid_to` | string \| null | Only if explicitly stated; null = open-ended |
| `confidence` | float | 0.0–1.0; minimum emit threshold 0.70 |
| `extraction_method` | string | deterministic \| llm \| hybrid |
| `evidence_span` | string | Verbatim supporting quote |
| `metadata` | object | Source-specific provenance fields |

Output: [`data/extraction/claims.jsonl`](../data/extraction/claims.jsonl)

## Timestamp semantics

| Field | Rule |
|-------|------|
| `observed_at` | When artifact was created/sent; prefer `artifact.timestamp` |
| `valid_from` | Set only when explicitly stated in text; else `null` |
| `valid_to` | Set only when explicitly stated; else `null` |
| Open-ended | Founder maps `null` → `9999-12-31` in HydraDB |

## Founder-side mapping (not owned by Data/ML)

The founder converts Claim records into HydraDB nodes using canonical IDs:

```
Claim.subject_mention → person:<resolved>
Claim.object_mention  → account:<resolved> | project:<resolved>
Claim.artifact_id     → :Artifact node (dsid namespace)
```

Reference synthetic fixture: [`data/fixtures/company.json`](../data/fixtures/company.json)

## Checkpoint deliverables

| Checkpoint | Data/ML delivers | Founder verifies |
|------------|------------------|------------------|
| #1 | This doc + 10 mention + 5 claim samples | Schema approval |
| #2 | 50 claims in `claims.jsonl` | Artifact → Claim → HydraDB → Query |
| #3 | `mention_inventory.json` | Entity resolution handoff |
