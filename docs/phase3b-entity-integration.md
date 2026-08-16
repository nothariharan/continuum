# Phase 3B — Real Entity Resolution Integration

Branch: `feature/phase3b-real-entity-integration`
Date: 2026-08-16
Base: master (includes merged Phase 3A)

## What was built

The machinery that consumes the teammate's identity-pair dataset and turns
resolver decisions into persisted canonical state:

```
identity features          (teammate: identity-pairs.jsonl)
  → FeatureVector          (pairs.py contract, guard-protected merge)
  → Resolver               (MERGE/KEEP_SEPARATE/REVIEW/ABSTAIN)
  → CanonicalEntity        (aliases, emails, usernames, sources, provenance)
  → EntityStore            (persisted :Entity nodes in HydraDB)
  → resolve_mention / aliases / sources / evidence queries
  → Claim bridge           (claim subject/object mentions -> canonical keys)
```

## New modules

- `continuum/entities/store.py` — HydraDB persistence for canonical entities
  (alias -> sources, emails, usernames, external ids, resolution provenance)
  + query layer: resolve_mention, get_entity_aliases, get_entity_sources,
  get_entity_evidence.
- `continuum/entities/bridge_claims.py` — claim -> canonical entity bridge.
  The Claim remains the evidence; canonical keys are added on top. Unresolved
  mentions are explicit (None + review flag), never guessed.
- `continuum/entities/taxonomy.py` — error taxonomy: FALSE_MERGE_EMAIL /
  FALSE_MERGE_NAME / FALSE_MERGE_ROLE_MAILBOX / FALSE_MERGE_SHARED_PROJECT /
  FALSE_MERGE_TOKEN_OVERLAP / FALSE_SPLIT_ALIAS / FALSE_SPLIT_INITIALS /
  FALSE_SPLIT_USERNAME / FALSE_SPLIT_CROSS_SOURCE_ID.
- `continuum/entities/regression_fixture.py` — 24-pair hand-labeled
  integration regression suite.
- `scripts/calibrate_entity_resolution.py` — threshold sweep
  (make calibrate-entity-resolution): merge threshold vs false-merge rate,
  false-split rate, review/abstain rates, accuracy.
- `scripts/entity_resolution_integration.py` — full real-data run
  (make entity-integration): inventory -> cluster -> store -> query -> bridge.

## Model changes

- `CanonicalEntity` now tracks per-alias source provenance
  (`alias_sources`) and `resolution_provenance` (why each merge happened).
- `EntityResolver.cluster()` attaches the MERGE verdicts that formed each
  cluster.
- Email matching is now **domain-family aware**: local-part equality is
  identity only within the same org (redwood.com/redwood.ai/...). This fixed
  the one false merge in the regression suite:
  `david.park@redwood.com` vs `david.park@acme.com` no longer merges.
- `StateQueryAdapter` now accepts an `entity_store` and exposes
  `resolve_entity` (real), `get_entity_aliases`, `get_entity_sources`,
  `get_entity_evidence` — still not wired to MCP.

## Results

### Integration regression suite (24 pairs, hand-labeled)

```
pair accuracy        0.71
SAME       P/R/F1    1.0 / 0.5 / 0.67
DIFFERENT  P/R/F1    0.75 / 0.9 / 0.82
FALSE MERGE RATE     0.0     (the critical metric)
FALSE SPLIT RATE     0.3     (safe misses: REVIEW/ABSTAIN on ambiguity)
error taxonomy: FALSE_SPLIT_USERNAME 1, FALSE_SPLIT_ALIAS 5, FALSE_MERGE_EMAIL 1 (fixed)
```

Remaining FALSE_SPLIT_* cases are conservative REVIEW/ABSTAIN decisions on
genuine ambiguity (e.g. er-003 @soham↔soham-dev reviews at 0.88 below the
0.90 merge threshold). These are safe misses — they never corrupt the graph.

### Real-data integration run (mention inventory)

```
mentions: 1,126    excluded: 254 (non-mention-shaped)
clusters: 87       max cluster: 9    mentions absorbed: 247
review pairs: 1,043   abstained: 177,662   separate: 454,380
clustering: 44.7s (O(n^2); candidate blocking will replace this)
store save: 22.2s    query sample: 45ms
claim bridge: 10 claims, 0 fully resolved, 5 partial (review), 5 unresolved
```

The claim bridge shows the real coverage gap: the inventory clusters and the
known-good fixture entities only partially overlap. Full claim resolution
waits for the teammate's identity-pair dataset + calibration.

## Teammate handoff readiness

When `data/entity_resolution/identity-pairs.jsonl` lands:

```
make eval-entity-resolution DATA=<file>     # accuracy + false merge/split
make calibrate-entity-resolution DATA=<file> # threshold operating curve
python scripts/entity_resolution_integration.py   # full pipeline re-run
```

No more architecture work needed on the consumption side.

## Tests

178/178 full suite. New: 11 integration tests (store roundtrip, alias
sources, provenance, claim bridge, taxonomy, domain-family guard, regression
fixture shape + false-merge-zero).
