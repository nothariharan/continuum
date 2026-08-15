# Phase 2A — Real Track 01 Dataset Reconnaissance

Status: **done**. HydraDB integration survives real-data load; Phase 1 graph regression passes.

## Goal

Acquire, inspect, sample, normalize, and experimentally validate the official
Hack Hydra Track 01 dataset. Build a reproducible pipeline and confirm the
Phase 1 harness keeps working on real data. **Not** building the claims graph,
entity resolution, MCP, UI, or full ingestion pipeline yet.

## Dataset

- **EnterpriseRAG-Bench** v1.0.0 — `github.com/onyx-dot-app/EnterpriseRAG-Bench`
- License: MIT (the alternative, Salesforce HERB, is CC-BY-NC-4.0 → non-commercial)
- Paper: arxiv.org/abs/2605.05253 · HuggingFace mirror: `onyx-dot-app/EnterpriseRAG-Bench`
- Release: `all_documents.zip` (1,256,181,062 bytes, sha256
  `9d1174928696ad08bc15f3f104739519de633c1605a4ec2034e0e3c0087bc5cd`)

## Repro pipeline

| command | does |
|---|---|
| `make dataset-info` | prints pinned release manifest summary |
| `make dataset-download` | downloads `all_documents.zip` to `data/raw/` (gitignored) and verifies sha256 |
| `make dataset-inventory` | writes `data/metadata/dataset_inventory.json` straight from the archive |
| `make dataset-sample` | writes `data/samples/phase2a-sample.jsonl` + report (360 artifacts) |
| `make dataset-quality` | writes `data/metadata/data_quality_report.json` |
| `make embedding-experiment` | writes `data/metadata/embedding_experiment.json` |

Modules under `continuum/dataset/`: `manifest`, `download`, `inventory`,
`artifact`, `quality`. Embedding/retrieval under `continuum/embed/` behind a
swap-able `EmbeddingProvider` interface. HydraDB artifact load under
`continuum/hydradb/artifacts.py`.

## Inventory (from the archive, 511,963 files)

| source | files | bytes | size range |
|---|---:|---:|---|
| slack | 285,605 | 964,465,933 | 9 – 17,596 |
| gmail | 121,390 | 860,188,084 | 48 – 17,431 |
| linear | 35,308 | 182,440,936 | 133 – 17,539 |
| google_drive | 25,108 | 178,644,645 | 54 – 22,744 |
| hubspot | 15,017 | 46,751,262 | 81 – 8,176 |
| fireflies | 10,173 | 117,756,071 | 126 – 42,281 |
| github | 8,052 | 38,236,614 | 245 – 13,952 |
| jira | 6,120 | 33,959,577 | 182 – 10,467 |
| confluence | 5,189 | 51,191,526 | 104 – 24,889 |
| **total** | **511,963** | **2,474,399,575** | |

Matches the track spec (≈500k docs, 9 sources). Files are `dsid_<32-hex>__<slug>.txt`
per source. `slack` docs are message threads (Noah/Zoe/Hannah/… + RedwoodBot),
`gmail` are RFC-style emails (`From:/To:/Date:/Subject:`), `github` are PR
descriptions, `linear`/`jira` are tickets, `fireflies` are meeting summaries,
`hubspot` CRM records, `confluence`/`google_drive` long-form docs.

## Canonical Artifact model

`continuum/dataset/artifact.py` → `Artifact` dataclass:

```
id          dsid_<32-hex>            (stable, dedup-able)
source      slack|gmail|linear|google_drive|hubspot|fireflies|github|jira|confluence
source_id   32-hex
type        source-specific (slack_message, gmail_message, …)
author      extracted where the format has it (gmail From:, fireflies attendees)
timestamp   header date, or slug-derived (unix-ts / YYYY-MM-DD) — provenance in metadata.ts_source
title       first line (matches slug for most sources)
content     full raw text
metadata    {noise, subject, attendees, slug, ts_source}
```

Normalization is deterministic: 360/360 sample records normalized, 0 rejected.

## Data quality (360-record sample)

- titles present: 360/360; authors: 33/360 (gmail only); timestamps: 116/360
  (gmail header 23 + slug 17, fireflies header 20 + slug 20, slack unix-slug 36)
- cross-source references are rich: 825 email addresses, 480 ticket refs
  (e.g. `ENG-5842`, `SUP-19344`), 198 URLs — the raw material for entity resolution later
- no `dataset_noise_document` flags observed in the sample (noise docs exist per the paper; will surface at full-corpus scale)

## Embedding experiment (`all-MiniLM-L6-v2`, 384-dim, corpus = 360)

| retriever | Recall@5 | Recall@10 | median query ms |
|---|---:|---:|---:|
| BM25 (lexical) | 0.750 | 0.875 | 2.8 |
| Dense (embeddings) | 0.625 | 0.625 | 19.5 |
| Hybrid (RRF) | 0.750 | 0.750 | 19.7 |

Index time: BM25 0.19 s, dense 19.5 s (CPU). Point lookup ~2 ms.

Reading: lexical wins on term-exact titles at this tiny scale; dense recovers
semantic paraphrases (e.g. "Redwood promise re: attempt-level billing") that
BM25 misses but the hybrid fusion keeps both. Plan: use hybrid retrieval once a
query layer exists; embed once, reuse. The `EmbeddingProvider` interface means
swapping models later is a one-line change.

## HydraDB artifact load

360 normalized Artifacts loaded as `:Artifact` nodes (ids namespaced at
`1_000_000_000+` to avoid colliding with the Phase 1 synthetic ids 1–8).

- load 360: ~670 ms · read-back all: ~100 ms · point lookup p50 2.3 ms / p95 2.9 ms / p99 3.0 ms
- 0 read-back mismatches; `data/metadata/dataset_inventory.json` + quality + experiment JSON are committed artifacts

HydraDB constraints discovered and worked around:
- node ids must be non-negative integers (map string dsid → int namespace)
- `UNWIND` merge patterns must match on `id` only; labels via `SET`
- aggregates limited to `count(*)` (no `count(a)`)
- no list/map/list-of-maps params; scalar params only
- deletes are slow (~155 ms/node); full-label `DETACH DELETE` exceeds the 30 s
  query limit once hundreds of nodes exist → chunked deletes by id range

## Phase 1 regression (all green)

1. reset → synthetic company → Phase 1 tests: **6 passed**
2. reset → real 360-artifact load → Phase 2A tests: **4 passed**
3. reset → synthetic company → Phase 1 tests again: **6 passed**

`scripts/seed_synthetic_company.py --reset` now reuses the chunked artifact
delete so it stays fast even with real artifacts present.

## Files

- `continuum/dataset/` — manifest, download, inventory, artifact, quality
- `continuum/embed/` — provider interface, sentence-transformers impl, BM25, dense/hybrid retrievers
- `continuum/hydradb/artifacts.py` — `:Artifact` load/read/delete
- `scripts/dataset_{info,download,inventory,sample,quality}.py`, `scripts/embedding_experiment.py`, `scripts/dataset_load_hydradb.py`
- `tests/phase2a/test_real_artifacts.py` — integration tests
- `data/raw/` (gitignored) — 1.25 GB archive · `data/samples/` — 360-record JSONL
- `data/metadata/` — `dataset_inventory.json`, `data_quality_report.json`, `embedding_experiment.json`

## Next (Phase 2B+)

Entity resolution across the rich cross-source references, the claims graph,
hybrid retrieval against HydraDB, then MCP/UI. The Artifact + `:Artifact` nodes
are the stable substrate for all of it.