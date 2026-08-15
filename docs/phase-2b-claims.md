# Phase 2B — Real Claims / Evidence Harness

Status: **in progress**. Shared contract defined, claim ingestion boundary
built, real-shaped claims load into HydraDB, state/provenance/conflict/
abstention verified on real-shaped data, Phase 1/2A regression green.

## Goal

Validate that real enterprise evidence can be transformed into trustworthy
claims and loaded into HydraDB with full provenance, before any extraction
automation or entity resolution exists. This is the founder side of Phase 2B;
mention/claim extraction precision/recall is the teammate's half (Gate 1/2).

## What was built (founder side)

### Shared contract — `continuum/claims/`

- `schema.py` — `Mention` and `Claim` dataclasses. Claim fields match the
  AGENTS.md contract exactly: `claim_id, artifact_id, subject_mention,
  predicate, object_mention, observed_at, valid_from, valid_to, confidence,
  extraction_method`. No canonical entity ids — mentions are intentionally
  unresolved until Phase 3.
- `validate.py` — strict boundary validation (id formats, ISO timestamps,
  confidence in [0,1], mention types). A malformed claim never reaches the
  graph.
- `io.py` — JSONL interchange format; the teammate's extraction pipeline
  writes claims.jsonl, the ingestion boundary reads it.

### Ingestion boundary — `continuum/hydradb/claims.py`

- Consumes contract-validated claims + a **manual resolution map**
  (`data/fixtures/phase2b/resolutions.json`, mention text → entity
  key/label). This is the Phase 2B "manually resolvable entities" scope;
  automatic resolution is Phase 3.
- Writes the Phase 1 graph shape: entity nodes, `:Claim` nodes,
  `SOURCED_FROM → Artifact → FROM → Source`, `ABOUT`, predicate rels with
  validity intervals, and **derived `CONTRADICTS` edges** (same object +
  predicate, overlapping validity, different resolved subjects).
- Every claim must trace to an artifact already in the graph (fixture key or
  real `dsid_` from the Phase 2A load) — evidence is never dangling.
- Read-back verification after load (zero-mismatch, like Phase 2A).
- Surgical reset: per-label delete scoped to the Phase 2B id range
  (1_000_000_000_000+), never touches Phase 1 (ids 1–N) or Phase 2A
  (1e9+) nodes.

### Query engine — `continuum/query/state.py`

- `resolve_state` / `resolve_state_on` / `resolve_conflicts` /
  `resolve_provenance` — the Phase 1 patterns generalized to any predicate
  (OWNS / MAINTAINS / REVIEWS / DEPENDS_ON) and any entity type, via a
  fixed rel allowlist (HydraDB cannot parameterize rel types/labels).
- Phase 1 query functions are untouched.

### Fixture — `data/fixtures/phase2b/`

Real-shaped, grounded in the actual EnterpriseRAG-Bench sample content
(Redwood's Optimize Conductor 2.0 release notes, CedarBank case study, Hosted
API key rotation thread, OrionAI transition checklist):

- 8 artifacts (confluence/gmail/slack/linear/fireflies)
- 9 claims: 3 OWNS on CedarBank with a **two-source handoff conflict**
  (Maya Patel → Camila Reyes), MAINTAINS/REVIEWS/DEPENDS_ON for predicate
  generalization, and OrionAI as the abstention target (resolved entity,
  zero claims)
- 10 manual resolutions (6 people, 2 accounts, 2 projects)

## HydraDB constraints discovered (documented per AGENTS.md rule 9)

- Label-less `MATCH (n)` is rejected → per-label deletes/queries.
- Dynamic labels/types must be allowlisted and interpolated, never passed
  as parameters.
- **Null values are rejected inside parameters** (even inside list-of-map
  batch rows) → open-ended validity is materialized as `9999-12-31`, the
  same convention Phase 1 already uses.
- `UNWIND MATCH CREATE` cannot be followed by another clause → rel validity
  is SET in a second per-row query, same as Phase 1's seed.
- `UNWIND MATCH CREATE` endpoints must carry exactly one label → rel
  templates interpolate subject/object labels from the allowlist.
- A stale persisted store can break all DELETEs with internal errors →
  full `make hydradb-reset` restores the known-good state (data is
  reproducible from scripts).

## Results (current state of the repo graph)

- Load: 9 claims, 8 artifacts, 9 sources, 9 entities, 63 relationships,
  0 read-back mismatches.
- Current state: CedarBank owner = Camila Reyes (latest valid_from wins).
- Historical: Maya Patel as of 2026-06-01.
- Conflict: CONFLICT, subjects [camila-reyes, may-patel], CONTRADICTS edges
  derived from the may-owns claim.
- Provenance: Gmail + Slack + Linear evidence chain per claim.
- Abstention: OrionAI → ABSENT.
- Predicate generalization: MAINTAINS (Diego → Optimize Conductor),
  DEPENDS_ON (Optimize Conductor → Hosted API) resolve correctly.

## Phase 2B benchmark (`docs/phase-2b-benchmark.json`)

| operation | p50 | p95 | p99 |
|---|---:|---:|---:|
| current_state (real) | 2.0 ms | 4.4 ms | 8.7 ms |
| historical_state (real) | 3.8 ms | 12.1 ms | 12.1 ms |
| provenance (real) | 5.7 ms | 7.7 ms | 10.8 ms |
| conflict (real) | 4.0 ms | 5.5 ms | 5.7 ms |
| Phase 1 reference (current) | 2.4 ms | 4.2 ms | 7.7 ms |

The real-claim path is within Phase 1's synthetic baseline range. These are
small-graph numbers, not targets.

## Regression status

- `tests/phase2b` — 11 passed
- `tests/phase1` — 6 passed
- `tests/phase2a` — 4 passed
- `tests/hydradb` — 2 passed (smoke read test scoped to its own ids, since
  Phase 1/2B entities now legitimately coexist in the same graph)
- Full suite `pytest tests -m hydradb`: **27 passed**

## Commands

```
make claims-load          # validate + resolve + load fixture into HydraDB
make claims-benchmark     # writes docs/phase-2b-benchmark.json
make test-phase2b         # Phase 2B integration tests
```

## Next (collaboration gate, not automatic)

Gate 2: teammate's first 20–50 real extracted claims (`claims.jsonl`
pointing at real `dsid_` artifacts) → load with the same boundary → joint
manual inspection of the full path:

```
raw artifact → normalized artifact → mention → claim → HydraDB → state → provenance
```

Only if that path is trustworthy does Phase 2B continue (contract lock,
extraction precision/recall, real-data query baseline). Then STOP and move
jointly to Phase 3 design.
