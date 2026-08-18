# PR #10 Review — Stabilization Sprint Baseline ("Before")

**Branch:** `feature/review-source-extraction-e2e` (review of `feature/source-extraction-e2e`, PR #10)
**Base commit (master):** `7995ecf0f2620ee7d9756bd195f7fcba77390a48`
**PR head commit:** `0e6ea4ef2755e9787f26881e9b14b5571f38e17e`
**Baseline captured:** after initial review, before any stabilization changes.

> This document is the permanent "before" record for the B1–B4 stabilization
> sprint. It is captured so that post-fix numbers can be proven to be an
> improvement rather than merely a change.

---

## 0. Environment

| Item | Value |
|---|---|
| Python | 3.12.10 |
| pytest | 9.1.1 |
| HydraDB | Docker image `ghcr.io/hydra-db/hydradb@sha256:db78309a...`, local single-node, port 7687/8443/9090 |
| Fireworks | `accounts/fireworks/models/gpt-oss-20b` via `https://api.fireworks.ai/inference/v1`, temperature 0 |
| Env vars | `FIREWORKS_API_KEY`, `CONTINUUM_LLM_BASE_URL`, `CONTINUUM_LLM_MODEL` (values not recorded; no secrets) |
| Test commands | `PYTHONPATH=. python -m pytest tests/pipeline/test_source_e2e_unit.py tests/phase2b/test_refinement_v2.py -q`<br>`PYTHONPATH=. python -m pytest tests/sources/test_source_extraction_e2e.py -q -k "not hydradb and not fireworks"`<br>`PYTHONPATH=. python -m pytest tests/sources/test_source_extraction_e2e.py -q -m hydradb`<br>`PYTHONPATH=. python -m pytest tests/sources/test_source_extraction_e2e.py -m fireworks -q` |

---

## 1. Baseline metrics

| Metric | Current |
|---|---|
| Extraction precision (vs gold) | 0.750 |
| Extraction recall (vs gold) | 0.857 |
| Artifacts | 10 |
| Extracted claims | 11 |
| Loadable claims | 8 |
| Rejected claims | 3 |
| Deterministic vertical, clean graph | 9/20 |
| Deterministic vertical, polluted graph | 7/20 |
| Fireworks calls during review | ~33 (20 test + 10 subset + 3 subset2) |
| Fireworks latency | p50 ~700 ms, max 2701 ms |
| Phase 1 regression | PASS (~173 s per test — pre-existing slow integration) |
| Full non-HydraDB suite | 236 passed |

---

## 2. Preserved failing examples (become regression fixtures)

### B1 — extraction quality
- `soham@company.com owns Acme` → subject mangled to `com` (regex boundary bug).
- `Subject: Acme ownership\n\nMorgan owns Acme.` → subject `ownership\n\nMorgan` (greedy whitespace).
- `From: Maya Patel <maya.patel@redwood.com>` → subject `Maya Patel <maya.patel@redwood.com>` (author not normalized).
- Consequence: legitimate Gmail CedarBank handoff claim rejected → Gmail provenance lost (se2e-07 fails).

### B2 — temporal validity
- `"Confirmed — I'm taking over CedarBank ownership from July 28."` → `valid_from` not populated; state falls back to artifact timestamp.
- `"When did Camila become owner?"` (se2e-11) returns `2024-10-07` instead of `2026-07-28`.
- `"Who owned CedarBank as of 2026-07-27?"` (se2e-16) returns Camila instead of Maya.

### B3 — entity resolution
- `resolve_entities_from_artifacts` contains literal alias whitelist + `keep_keys` deletion of unseen entities.
- `@soham` vs `soham@company.com` resolves to the same entity in the extraction path but returns `uncertain` in the question path (EntityResolver).

### B4 — HydraDB isolation
- `DETACH DELETE` intermittently raises `Neo.DatabaseError.General.UnknownError` under polluted state.
- Clean graph → 9/20; polluted graph → 7/20; outcome depends on database history.

---

## 3. Question matrix (deterministic vertical, clean graph)

| Q | Category | Expected | Got | Status |
|---|---|---|---|---|
| se2e-01 | single-hop | Camila Reyes | Camila Reyes | OK |
| se2e-02 | temporal | Maya Patel | Maya Patel | OK |
| se2e-03 | single-hop | Soham Ratnaparkhi | Soham Ratnaparkhi | OK |
| se2e-04 | cross-source | Priya | Soham Ratnaparkhi | FAIL |
| se2e-05 | temporal | Morgan | Morgan | OK |
| se2e-06 | conflict | CONFLICT: Morgan or Priya | conflict: ... | OK |
| se2e-07 | provenance | 2 claim(s) via Gmail, Slack | Slack | FAIL |
| se2e-08 | multi-hop | Slack | Slack | OK |
| se2e-09 | entity-resolution | same | uncertain | FAIL |
| se2e-10 | abstention | unknown - abstain | unknown | FAIL |
| se2e-11 | temporal | 2026-07-28 | Camila Reyes | FAIL |
| se2e-12 | provenance | claim | conflict: ... | FAIL |
| se2e-13 | single-hop | Soham Ratnaparkhi\|Morgan | Soham Ratnaparkhi | OK |
| se2e-14 | cross-source | Gmail\|Slack | Camila Reyes | FAIL |
| se2e-15 | conflict | CONFLICT | conflict: ... | OK |
| se2e-16 | temporal | Maya Patel | Camila Reyes | FAIL |
| se2e-17 | single-hop | Camila Reyes | Camila Reyes | OK |
| se2e-18 | entity-resolution | same | uncertain | FAIL |
| se2e-19 | abstention | unknown - abstain | unknown | FAIL |
| se2e-20 | multi-hop | gmail artifact | Camila Reyes | FAIL |

9/20 correct.

---

## 4. Scope boundary (frozen)

Allowed in this sprint ONLY:

1. B1 — extraction quality
2. B2 — temporal validity
3. B3 — entity resolution minimum correction
4. B4 — E2E isolation
5. Regression tests for those fixes
6. Full re-validation
7. Documentation and merge decision

Not allowed: OAuth, webhooks, UI, MCP, benchmark expansion, new source types, new claim predicates, unrelated refactors.
