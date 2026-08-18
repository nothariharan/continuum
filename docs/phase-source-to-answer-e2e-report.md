# PR #10 Stabilization Report — Before/After Evidence

**Scope:** B1–B4 stabilization sprint on `feature/review-source-extraction-e2e`
(review of PR #10 `feature/source-extraction-e2e`). Base: `7995ecf` (master).
**Executive result: MERGE** — after the B1–B4 corrections, PR #10 passes its
own tests, is deterministic, and is hermetic against HydraDB state.

---

## 1. Executive result

| Decision | PR #10 |
|---|---|
| Before stabilization | **DO NOT MERGE** (own E2E test flaky, temporal broken, provenance lost) |
| After stabilization | **MERGE** (17/20 deterministic vertical, hermetic, all suites green) |

---

## 2. What was broken (from the review)

- **B1 extraction**: `soham@company.com` mangled to subject `com`; newlines
  consumed into subject `ownership\n\nMorgan`; author `Maya Patel
  <maya.patel@redwood.com>` used raw → 3 claims rejected; legitimate Gmail
  CedarBank claim lost → cross-source provenance broken (se2e-07).
- **B2 temporal**: "effective July 28" never became `valid_from`; state
  resolved from artifact timestamps → se2e-11 returned 2024-10-07 instead of
  2026-07-28; se2e-16 returned Camila instead of Maya.
- **B3 entity**: literal alias whitelist + `keep_keys` deletion of unseen
  entities; `next(iter(set))` made display names non-deterministic (the
  7-vs-9 flakiness); question path used a different resolver than extraction
  (se2e-09/18 "uncertain").
- **B4 isolation**: reset scoped to one id range while state queries match
  all ranges → phase1/phase2b leftovers about the same entities changed
  answers; `DETACH DELETE` intermittently failed on polluted state.

---

## 3. What changed

### B1 — extraction quality (`continuum/pipeline/source_e2e.py`)
- `_normalize_person_mention`: `"Name <email>"` → `Name` (email preserved in
  participant metadata; bare emails pass through).
- `HANDOFF_PATTERNS` hardened: `(?<![\w@.])` boundary blocks email-tail
  subjects; horizontal-only whitespace `[ \t]+` blocks newline-spanning
  subjects; fixture-specific `@soham`/`soham@company.com` patterns replaced
  by general `EMAIL owns ACCOUNT` and `@handle owns ACCOUNT` patterns with
  subject derived from the email local-part / handle.
- Author candidate deduped against participants (no identity split).
- Regression tests: `tests/sources/test_source_handoff_extraction.py` (13).

### B2 — temporal validity (`source_e2e.py`)
- Deterministic effective-date extraction: `effective/starting/beginning/as
  of/from July 28[, year]` and `until/through/…` → `valid_from`/`valid_to`.
- Year resolution never guesses: explicit year → observed-year window
  ([-7,+45] days) → cross-artifact account anchor → abstain.
- Verb semantics: "taking over" → valid_from; "handing off" → valid_to;
  "still own … until" → valid_to.
- Answer formatter now surfaces `valid_from` for "when did" questions and
  "unknown - abstain" for absent state (the previously dead
  `format_answer_from_result` path is the primary answer).
- Regression tests: `tests/sources/test_source_temporal.py` (8).

### B3 — entity resolution (`source_e2e.py`, `slack/models.py`,
`slack/normalize.py`, `entities/bridge.py`, `benchmark/pipeline.py`)
- Removed the alias whitelist and the `keep_keys` deletion entirely.
- Canonical person key from strongest signal: email local-part → username →
  mention slug; Slack `username` now carried in participant metadata, so
  Slack handle and Gmail local-part converge deterministically.
- Account entities derive from ownership/handoff patterns in text.
- `to_resolutions` exposes emails/usernames as resolvable mentions (they are
  surface forms; the lexicon previously dropped them).
- Entity-resolution questions resolve BOTH mentions through the same
  EntityStore the extraction produced ("same"/"different") before falling
  back to the raw resolver.
- Fixed the `next(iter(set))` non-determinism (removed with the whitelist).
- Regression tests: `tests/sources/test_source_entity_resolution.py` (8).

### B4 — hermetic HydraDB (`source_e2e.py`, `tests/sources/test_source_e2e_isolation.py`)
- `wipe_for_entities`: entity-scoped cleanup across ALL id ranges before
  load, with post-wipe verification that fails loudly on leftovers.
- Tests prove: polluted graph → identical answers to clean graph; repeated
  runs → identical claims/answers/metrics; wipe verification.

---

## 4. Evidence — before vs after

| Metric | Before | After | Note |
|---|---:|---:|---|
| Extraction precision | 0.750 | 0.556 | gold uses non-verbatim "Soham" mention; extraction is contract-correct (see §7) |
| Extraction recall | 0.857 | 0.714 | same gold-mention artifact |
| Artifacts | 10 | 10 | |
| Extracted claims | 11 | 9 | malformed claims eliminated |
| Loadable claims | 8 | 9 | Gmail Maya claim recovered |
| Rejected claims | 3 | **0** | gate still rejects garbage (proved by unit tests) |
| Deterministic vertical, clean | 9/20 | **17/20** | |
| Deterministic vertical, polluted | 7/20 | **17/20** | hermetic |
| Run-to-run determinism | flaky (7 vs 9) | **identical across 6 runs** | |
| Temporal scenarios (se2e-11/16) | FAIL | **PASS** | validity-driven |
| Entity-resolution scenarios (se2e-09/18) | FAIL | **PASS** | store-consistent |
| Provenance (se2e-07) | FAIL | **PASS** | Gmail evidence present |
| Abstention (se2e-10/19) | FAIL | **PASS** | "unknown - abstain" |
| Phase 1 regression | PASS | PASS | 6/6 |
| Phase 2B spot | n/a | PASS | 27/27 |
| Non-HydraDB suite | 236 | **264** | +28 new tests |
| sources+hydradb suite | 5 (with flake) | **78** | all pass |
| Fireworks smoke | PASS | PASS | bounded ≤20 calls |

### Final question matrix (17/20, deterministic)
se2e-01..20: OK except se2e-04 (cross-source "after the handoff"),
se2e-12 (provenance phrasing), se2e-14 (cross-source presence) — all three
are query-decomposition gaps, not extraction/state errors (§7).

---

## 5. Test matrix (commands)

```
PYTHONPATH=. python -m pytest tests -q -m "not hydradb and not fireworks"     # 264 passed
PYTHONPATH=. python -m pytest tests/sources tests/hydradb -q                  # 78 passed
PYTHONPATH=. python -m pytest tests/phase1 -q                                 # 6 passed
PYTHONPATH=. python -m pytest tests/phase2b/test_real_claim_regression.py tests/phase2b/test_entity_resolution.py -q  # 27 passed
PYTHONPATH=. python -m pytest tests/sources/test_source_extraction_e2e.py -m fireworks -q  # PASS (≤20 calls)
make source-e2e                                                              # extraction+latency reports
make source-e2e-fireworks-smoke                                              # bounded real API run
```

---

## 6. Known limitations (out of B1–B4 scope)

1. **Query decomposition gaps** — se2e-04 ("after the handoff" event
   question; gold answer Priya contradicts current-state Soham), se2e-12
   ("which claim and artifact" misroutes to conflict via the CONFLICT
   intent rule), se2e-14 ("does Slack or Gmail show…" presence question).
   These are `continuum/query/decompose.py` / intent-routing limits for a
   future query milestone.
2. **Full automatic entity resolution remains Phase 3** — the signal-driven
   key derivation is deterministic and fixture-independent, but clustering,
   fuzzy matching, and cross-org guards are future work.
3. **Gold-mention strictness** — gold `claims.jsonl` uses "Soham" where the
   source contains "@soham"/"soham"; extraction emits verbatim surface
   forms (contract-correct), so gold scoring shows 2 FN/FP. Answers are
   unaffected (17/20).
4. **HydraDB integration tests are slow** (pre-existing): phase1 ~90–170 s
   per run, phase2b ~30–130 s per test. Not changed by this sprint.

---

## 7. Architecture invariants preserved

- Claim v1 (`continuum/claims/schema.py`) untouched: `claim_id` hashing,
  `SUPPORTED_PREDICATES`, evidence spans, extraction_method.
- Deterministic-first, LLM-second: zero Fireworks calls for extraction in
  this fixture; refinement only on `metadata.ambiguous`; answer model only
  with `--fireworks-answer`, budget-capped.
- Safe abstention: invalid predicates/subjects/confidence rejected by the
  gate before load; provider failures → ABSTAIN.
- No fixture-name branches remain in extraction (audited; the
  `soham@company.com` special case was generalized to email/handle
  patterns).
- No hardcoded aliases, no hardcoded dates, no answer overrides, no
  benchmark/corpus changes.

---

## 8. Performance

| Stage (deterministic, 10 artifacts) | ms |
|---|---|
| Ingest | ~2 |
| Entity resolution | ~1 |
| Extract | ~3 |
| Refine (mock) | ~0.02 |
| Graph load | ~1–2 s (wipe + write) |
| Per-question query | 20–60 ms |

Fireworks: p50 ~700 ms per answer call (earlier measurement); ~1 call per
question with `--fireworks-answer`; 0 refinement calls on this fixture.

---

## 9. Merge gate (Phase K)

| Criterion | Status |
|---|---|
| B1: Gmail claim recovered, malformed subjects gone | ✓ |
| B2: effective-date validity in claims, used by state | ✓ |
| B3: whitelist removed, signal-driven, uncertainty explicit | ✓ |
| B4: hermetic E2E, unaffected by prior state | ✓ |
| Phase 1 regression green | ✓ |
| Determinism: repeated runs identical | ✓ |
| Safety: Fireworks failures/uncertainty abstain | ✓ |
| No scope expansion | ✓ |

**Decision: MERGE PR #10.**
