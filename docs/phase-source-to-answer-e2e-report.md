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

---

## 10. Post-merge validation (Phase L) — COMPLETE

**Final master SHA:** `f3044c7b29877bc583526874f939319b9c34cf97`
(merge commit: PR #10 `0e6ea4e` + stabilization `995e0a9`)

| Validation item | Result |
|---|---|
| 1. master points to merged stabilization commit | ✓ `f3044c7` |
| 2. Full non-HydraDB suite | ✓ 264 passed, 68 deselected (4m36s) |
| 3. Source + HydraDB integration suite | ✓ 78 passed (4m25s) |
| 4. Deterministic E2E repeats identically | ✓ 17/20 × 6 runs |
| 5. Slack/Gmail extraction is automatic + claim-based | ✓ 10 artifacts → 9 claims, 0 rejected (`deterministic-v2`/`deterministic-handoff`) |
| 6. Temporal handoff correct | ✓ se2e-11 → 2026-07-28; se2e-16 → Maya |
| 7. Conflict stays conflict when ambiguous | ✓ se2e-06/15 → CONFLICT (both claims preserved) |
| 8. Entity resolution deterministic | ✓ se2e-09/18 → same (store-consistent) |
| 9. Provenance reaches original artifacts | ✓ se2e-07 → 3 claim(s) via Gmail, Slack (dsid artifacts) |
| 10. Fireworks smoke bounded + passes | ✓ 1 passed, ≤20 calls, temp 0 |
| 11. No benchmark artifacts modified | ✓ (report JSONs restored; zero diff) |
| 12. Working tree clean | ✓ only pre-existing untracked files |

### Remaining 3/20 query-decomposition failures (deterministic, known)

| Q | Question | Expected | Got | Root cause |
|---|---|---|---|---|
| se2e-04 | Who owns Acme now **after the handoff**? | Priya | Soham Ratnaparkhi | event-anchored question; gold answer conflicts with current state (se2e-03 says Soham is current) |
| se2e-12 | Which **claim and artifact** support Soham owning Acme? | claim | CONFLICT | "which claim" matches the CONFLICT intent rule; provenance phrasing not detected |
| se2e-14 | Does **Slack or Gmail** show the CedarBank handoff? | Gmail\|Slack | Camila Reyes | cross-source presence question; falls through to current state |

All three live in `continuum/query/decompose.py` intent routing / question
semantics — the query layer, not extraction or state.

### Exact remaining technical blockers

1. **Query decomposition gaps** (3/20 above) — intent routing for
   event-anchored ("after the handoff"), provenance-phrased ("which claim
   and artifact"), and cross-source presence ("does Slack or Gmail show")
   questions.
2. **Retrieval stub** — the vertical answers from loaded claims; BM25 over
   the ingested corpus is not wired into `answer()`.
3. **Full automatic entity resolution** — signal-driven key derivation is
   in place; broad clustering (fuzzy similarity, cross-org local-part
   guards, REVIEW/ABSTAIN decisions at scale) is Phase 3.
4. **HydraDB integration test speed** — phase1/phase2b tests take ~1–3 min
   each (pre-existing; not a correctness issue).

### Production-shaped now

- Automatic Slack/Gmail → canonical Artifact → deterministic claim
  extraction → validated load → HydraDB graph → temporal/conflict state →
  provenance → deterministic or Fireworks-backed answers.
- Safe abstention, bounded model usage, deterministic-first extraction,
  hermetic test lifecycle, Claim v1 contract.

### Still fixture-only / live-unwired

- **Live Slack/Gmail sync (OAuth, webhooks) — NOT implemented.** All
  source data is fixture JSON in `data/fixtures/sources/`.
- Fireworks refinement (predicate disambiguation) is wired but never
  triggered by the current fixture (0 ambiguous claims).
- BM25/dense retrieval over the corpus — not part of this vertical.
- MCP / UI — not started.

**STOP. No further work without a new decision.** Next highest-value step:
fix the 3 query-decomposition gaps (`decompose.py` intent routing), then
re-run the 20-question gold set aiming for 20/20.
