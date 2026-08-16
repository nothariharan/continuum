# Phase 3 — Entity Resolution Core (founder branch)

Branch: `feature/entity-resolution-core`
Date: 2026-08-16

## What was built

The deterministic core of the entity-resolution subsystem (Phase 3), built
on stable `master` so the teammate's data/evaluation work (`feature/data-evaluation`)
never blocks it.

```
continuum/entities/
    models.py       EntityCandidate, IdentitySignals, FeatureVector, EntityMatch,
                    CanonicalEntity, ResolutionDecision, ResolutionVerdict
    candidates.py   CandidateIndex (cheap deterministic top-N lookup)
    scoring.py      deterministic scoring table + pluggable feature slots
    resolver.py     EntityResolver: MERGE / KEEP_SEPARATE / REVIEW / ABSTAIN
    bridge.py       CanonicalEntity -> resolutions format (claim-loading input)
    fixtures.py     tiny manually-labeled fixture
continuum/query/semantic.py   Y10: the future MCP/API contract (not wired)
```

## Design rules

- Candidate generation is cheap; expensive reasoning only on the ambiguous tail.
- The resolver connects candidates — it never invents entities.
- CanonicalEntity is non-destructive: every alias, mention, email, username,
  external ID, and source is preserved.
- False merges are the critical failure mode → conservative thresholds.
- ABSTAIN/REVIEW are first-class outcomes, matching the product thesis.

## Scoring table (deterministic)

```
email local-part ↔ email local-part      0.97
email local-part ↔ username base         0.92
same external ID                         0.90
username base match                      0.88
full-name match (initials ok)            0.85
>=2 shared name tokens                   0.80
1 shared name token                      0.55
source overlap boosts weak scores        +0.05 (cap 0.6)
```

Decision rules: MERGE ≥ 0.90; KEEP_SEPARATE on distinct full names with no
identity signal; REVIEW on shared-but-inconclusive; ABSTAIN otherwise.
Cluster joins at the 0.80 tier only when the cluster has an identity anchor
(email/username/external id).

## Fixture (data/fixtures/phase3/identity-fixture.json)

The AGENTS.md canonical example: `Sam`, `@soham`, `S. Ratnaparkhi`,
`soham-dev`, `soham@company.com` + hard negatives (Maya Chen vs Maya Patel,
Sarah Chen vs Sarah Liu).

Deterministic outcome (conservative):
- anchored core merges: `@soham`, `soham-dev`, `soham@company.com`
- `Sam` / `S. Ratnaparkhi` stay REVIEW — single-token links are genuinely
  ambiguous and must not auto-merge (this is the correct abstention).

## Real-data validation (mention inventory)

`python scripts/entity_resolution_real.py` over the 1,126 mention-shaped
inventory entries:

```
merged clusters: 88      review pairs: 1,047
keep-separate: 410,524   abstained: 221,513
mentions absorbed: 249 (22.1%)   max cluster: 9
```

Verified clusters: Ben Carter family (Ben + 8 email variants), Marissa Cole,
Karthik Iyer, Jonas Weber, Monica Patel, Dev Patel.

### Four cascade bugs found and fixed on real data

1. **Empty-local-part email collision** — the inventory stores `@Arun` as an
   "email"; empty local parts collided → every @username merged. Fixed:
   EMAIL_RE validation.
2. **Role-suffix chain merges** — `(Redwood AE)` tokens shared by every AE
   mention → chain merges. Fixed: ROLE_SUFFIX_RE stripping in tokenization.
3. **TLD token bridging** — email mentions contributed `com`/`io` tokens →
   unrelated clusters bridged. Fixed: emails contribute local-part tokens only.
4. **Role-mailbox merges** — `procurement@*` all shared local part. Fixed:
   ROLE_MAILBOXES exclusion (functional accounts are not people).

Also: mention-shape guard (content blobs excluded), self-referential
external-id filter (inventory stores the mention itself as an external ID),
anchored-join raised to the 0.80 name-tokens tier.

## Y10 semantic interface (future MCP/API)

`continuum/query/semantic.py` defines the contract without wiring MCP:

```
resolve_entity(mention) -> canonical entity key      (Phase 3 bridge)
get_current_state(entity_key, predicate)
get_state_as_of(entity_key, date, predicate)
get_history(entity_key, predicate)
get_conflicts(entity_key, predicate)
get_evidence(entity_key, predicate)                  (provenance chain)
get_dependencies(entity_key)                         (DEPENDS_ON traversal)
```

Every method delegates to the stable query layer and returns the canonical
result envelope. Future MCP/HTTP is a thin adapter over this — never a second
implementation.

## Status

```
Entity candidate generation   ✅ (cheap, deterministic, ~ms scale)
Scoring framework             ✅ (pluggable feature slots ready for teammate data)
Resolver decisions            ✅ (MERGE/KEEP_SEPARATE/REVIEW/ABSTAIN)
Canonical entity graph        ✅ (non-destructive aliases)
Bridge to claim loading       ✅ (resolutions format)
Real-data validation          ✅ (88 clean clusters, 4 bugs fixed)
Semantic interface (Y10)      ✅ (defined, not wired)
Regression                    ✅ (104/104 tests)
```

## Next steps

- Consume teammate's `identity-pairs` feature file via the FeatureVector
  slots (embedding_similarity, cooccurrence) once the gold set is stable.
- Calibrate thresholds against the labeled 87-pair eval set.
- Y8: end-to-end real question via entity resolution → graph → state.
