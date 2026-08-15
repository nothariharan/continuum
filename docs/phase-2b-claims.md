# Phase 2B — Real Claims / Evidence Harness

Status: **contract v1 locked; Gate 2 checkpoint verdict: STOP claim-scale,
keep mention-scale**. Both halves are merged on master: extraction pipeline
(teammate, `continuum/extract/` + `continuum/eval/`) and the ingestion/state
side (founder, `continuum/claims/` + `continuum/hydradb/claims.py` +
`continuum/query/state.py`). The shared contract is single-sourced in
`continuum/claims/schema.py`; `continuum/extract/schemas.py` re-exports it.

## Gate 2 checkpoint result (checkpoint50, `scripts/checkpoint_claims.py`)

The teammate's top-50 extracted claims were run through the full graph gate:
contract validation → artifact present in HydraDB → mentions manually
resolvable → observation time resolvable. Report:
`data/metadata/checkpoint50_report.json`.

**0 of 50 claims are graph-loadable.** Rejection breakdown:

- 38 unresolvable **subject** mentions — doc titles, truncated ticket
  titles, roles/teams ("Head", "Eng", "Finance Ops"), or generic words
  ("finance", "incidents")
- 11 unresolvable **object** mentions — single generic words ("model",
  "tokens", "batching", "place", "treaty") or ticket titles
- 1 missing observation time (Ravi → Oakbridge, the only structurally
  plausible claim)

Interpretation: the deterministic/hybrid claim patterns bind artifact
*titles* to *fragments of the "X depends on Y" / "X blocks Y" sentence*,
which are not entity pairs. Extraction confidence (0.80–0.84) does not
measure graph quality. Claim precision is unmeasured (ground truth contains
1 claim) and by inspection is low for DEPENDS_ON/ASSIGNED_TO.

Per AGENTS.md Gate 2 ("if this fails, STOP. Do not scale"):

- The **mechanical path is proven** (9 hand-written real-shaped claims load,
  resolve, conflict, provenance — all green).
- The **claim extraction is not graph-grade yet**. Do not scale claim
  ingestion until the extractor emits entity-pair claims (person → account/
  project/ticket) with evidence spans and timestamps.
- **Mention extraction is healthy** (F1 0.82 on the labeled set, recall
  0.95) and `mention_inventory.json` is ready as Phase 3 input.

## Goal

Validate that real enterprise evidence can be transformed into trustworthy
claims and loaded into HydraDB with full provenance, before any extraction
automation or entity resolution exists. This is the founder side of Phase 2B;
mention/claim extraction precision/recall is the teammate's half (Gate 1/2).

## What was built (founder side)

### Shared contract — `continuum/claims/` (contract v1, single-sourced)

- `schema.py` — canonical `Mention` and `Claim` dataclasses. Claim fields:
  `claim_id, artifact_id, subject_mention, predicate, object_mention,
  observed_at, valid_from, valid_to, confidence, extraction_method,
  evidence_span, metadata`. Predicates: OWNS / MAINTAINS / LEADS /
  ASSIGNED_TO / BLOCKS / DEPENDS_ON / REVIEWS. No canonical entity ids —
  mentions are intentionally unresolved until Phase 3. Stable ids are
  16-hex sha256 hashes (or `claim:`/`mention:` slugs for hand-written
  fixtures). `continuum/extract/schemas.py` re-exports these classes so both
  sides share one definition.
- `validate.py` — strict boundary validation (id formats, real ISO dates
  when present, nullable timestamps per v1, confidence in [0,1], required
  `evidence_span`). A malformed claim never reaches the graph.
- `io.py` — JSONL interchange format; the extraction pipeline writes
  claims.jsonl, the ingestion boundary reads it.

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

## Claim-handoff verifier — `make checkpoint-claims`

The founder's feedback loop to the extraction side. For every candidate
claim in `data/extraction/claims.jsonl` it classifies exactly why the claim
can or cannot enter the graph, per claim, with reasons:

| code | meaning |
|---|---|
| `MALFORMED_ID` | claim_id / artifact_id violates the contract format |
| `INVALID_SUBJECT` | subject mention empty, or has no manual resolution (not an entity name) |
| `INVALID_OBJECT` | object mention empty, or has no manual resolution |
| `INVALID_PREDICATE` | predicate outside the supported vocabulary |
| `MISSING_ARTIFACT` | artifact_id not present in the HydraDB graph |
| `INVALID_TIMESTAMP` | timestamp present but not a real ISO date; or valid_to < valid_from |
| `MISSING_TIMESTAMP` | no observed_at and the artifact has no timestamp |
| `UNSUPPORTED_ENTITY_PAIR` | mentions resolve, but the label pair is not canonical for the predicate |
| `CONTRACT_VIOLATION` | anything else the canonical validator rejects |

Report: `data/metadata/claim_handoff_report.json`. Current run against the
611 extracted claims: 455 `MISSING_TIMESTAMP`, 156 `INVALID_SUBJECT`, 0
graph-loadable — this is the precise signal the extractor needs (emit
entity-pair claims with timestamps; title-fragment pairs are rejected).

### Graph-loadability is encoded, not judged

A claim is graph-loadable iff Continuum can represent it without inventing
entities, inventing timestamps, or violating the canonical
predicate/entity constraints (`ENTITY_PAIR_RULES` in
`continuum/hydradb/claims.py`):

- OWNS: Person → Account/Project
- MAINTAINS: Person/Team → Account/Project/Service
- LEADS: Person → Account/Project/Team
- ASSIGNED_TO: Person → Account/Project
- REVIEWS: Person → Account/Project
- BLOCKS: Person/Project → Project
- DEPENDS_ON: Project/Service → Project/Service

The manual resolution maps (`resolutions*.json`) are **test aids only** —
they prove real claim → canonical entity → HydraDB → state query. They are
not entity resolution (Phase 3).

## Known-good real-claim fixture — `data/fixtures/phase2b_real_claims.jsonl`

10 claims I hand-validated against the actual EnterpriseRAG-Bench artifacts
(real `dsid_*` references, evidence spans quoted verbatim):

- current ownership: Maya Patel OWNS LucentGrid (fireflies 2027-02-11)
- historical: LucentGrid OWNS as-of 2027-02-11 → Maya; as-of 2026-01-01 → ABSENT
- provenance: Acme Health OWNS → claim → gmail artifact → source chain
- conflict: Neha Kapoor vs Priyom Das OWNS Acme Health (real ambiguity in
  the MSA thread — the engine reports CONFLICT, keeps both claims)
- abstention: CedarBank (resolved, unclaimed) → ABSENT
- non-OWNS predicates: MAINTAINS (Ravi → Skyline, Olga → Acme Analytics,
  Jonas → Acme Health), LEADS (Jasmine → Acme Payments, Maya Chen →
  Skyline), ASSIGNED_TO (Ethan Cole → LucentGrid)

The loader auto-links referenced real artifacts to `:Source` nodes so the
provenance chain holds for real data. Commands:

```
make real-claims-load          # requires 360 artifacts loaded (make dataset-load-hydradb)
make real-claims-benchmark     # writes docs/phase-2b-real-benchmark.json
```

Real-claim benchmark: ingestion (write + verify) ~12.6 s; current-state p50
4.5 ms, historical p50 4.0 ms, provenance p50 9.5 ms, conflict p50 6.0 ms.
Still small-graph numbers; no optimization until there is real workload.

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

Gate 2 verdict is STOP for claim-scale: the extraction pipeline needs
entity-pair claims before more claims can enter the graph. Recommended
teammate changes:

1. Restrict claim emission to mentions that are real entity names (person /
   account / project / ticket keys), not titles or single generic words.
2. Make ASSIGNED_TO/OWNS/LEADS the primary targets (they produce the
   enterprise-state semantics) and require an observed_at (or artifact
   timestamp) on every emitted claim.
3. Expand the ground truth beyond 1 claim so claim precision/recall is
   actually measurable.

Then re-run `scripts/checkpoint_claims.py`; the boundary itself needs no
changes. Only after a meaningful share of checkpoint claims load and resolve
should Phase 2B scale and Phase 3 (entity resolution) design start.
