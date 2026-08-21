# Continuum — Hackathon Execution Progress Notes

Tracks progress against `hackathon-execution-plan.md`. Re-read this before resuming.

**Last updated:** Wed Aug 19 2026 (merge train complete)
**Branch:** master (merged, clean of feature work)
**Baseline:** dfc72bd → now `1677577` (9 merge commits)

---

## Where we are

**MERGE TRAIN COMPLETE — all 9 batch PRs merged to master.**

| PR | Branch | Commit |
|---|---|---|
| #19 | phase2b-third-person-entities | feat(extraction): support third-person ownership entity resolution |
| #20 | slack-reliability | feat(slack): harden event delivery and memory worker reliability |
| #21 | slack-product-answer | feat(slack): add structured evidence-backed answer blocks |
| #22 | cross-source-memory | test(pipeline): lock cross-source memory merge behavior |
| #23 | entity-resolution-hardening | fix(entities): harden cross-source identity convergence |
| #24 | benchmark-scorer-v2 | fix(benchmark): version scorer and guard empty answers |
| #25 | query-graph-export | feat(query): add read-only knowledge graph export |
| #26 | mcp-semantic-adapter | feat(delivery): add semantic MCP adapter |
| #27 | demo-story | feat(demo): add reproducible company-memory story |

Safety reference: branch `snapshot/pre-merge-dfc72bd` holds the full pre-merge working tree.

Working tree on master contains ONLY the DO-NOT-COMMIT harness noise (benchmark sample reports, `source_e2e_*.json`, generated metadata) + the two HACKATHON docs (untracked). No feature files remain uncommitted.

**Remaining (blocked on user resources, not code):** Batch 0 manual credential rotation · Batch 4 live Gmail OAuth · Batch 6.2 overnight 500Q run · FINAL live-Slack demo (needs creds) + the `before`/`conflict` temporal flourishes (Phase 4).

**Next action on resume:** rotate credentials → live Slack smoke → live Gmail OAuth → overnight `make benchmark-full-v1-baseline` → benchmark analysis → UI MVP (consuming QueryService / graph_export / MCP adapter / answer envelope).

---

## DONE so far

### Batch 0 — Secret hygiene (COMPLETE, except manual rotation)
- `.env` untracked + git-ignored (`git check-ignore .env data/ingestion/` prints both). ✓
- `.env.example` = names only, no values. ✓
- No secret-shaped strings in tree or git history (`xox[bp]-`, `xapp-`, `fw_`, signing secret, PEM). ✓
- No logger/print token leakage. ✓
- **PENDING (manual, cannot automate):** rotate the actual creds at Fireworks + Slack dashboards. Do this before any screen-share/record. Replace values only in `.env`.

## Batch 2 — Slack loop reliability (CODE DONE + VERIFIED)

Files changed:
- `continuum/sources/slack/live.py` — `SlackWebClient._call` bounded exponential-backoff + jitter retry (429/5xx/408 + network), honors `Retry-After`, typed `SlackAPIError` after exhaustion. Configurable `max_retries`/`base_backoff`/`max_backoff`/`timeout`.
- `continuum/sources/events.py` — `mark_processed` atomic (temp+rename); `load()` skips malformed lines; `SourceEvent` gains `attempts`.
- `continuum/sources/sync.py` — `save_cursor` atomic (temp+rename).
- `continuum/pipeline/memory_worker.py` — `max_attempts=3` bounded retry for poison events (missing native_id / record-not-found / ingest error); fixed skipped→failed bug (now `processed`); `run_forever` traps KeyboardInterrupt + survives per-iteration errors + `stop_event`.

Tests: `test_slack_live_retry.py` (7), `test_memory_worker_reliability.py` (4), `test_event_queue_extra.py` updated.

VERIFY (Batch 2): INV-2 **325 passed**; hydradb worker+harness **6 passed**; INV-1 **20/20** unchanged. ✓

Deferred (low priority): Socket-Mode reconnect in `run_slack_bot.py`; cursor-after-ingest reordering; separate `failed-events.jsonl`.

---

## Batch 3 — Product-grade Slack answer (CODE DONE + VERIFIED)

- Rewrote `continuum/delivery/slack_formatter.py::format_slack_answer` to emit structured Block Kit sections — `Answer` / `Sides` (conflict only) / `Why` / `State` / `Confidence` — built only from the structured envelope (status/value/history/valid_from/confidence/evidence). `Why` = source + artifact-kind; `State` = history transition `A → B (effective <date>)`; `Confidence` = High/Medium/Low/None from status+confidence. No model text, no CoT.
- Tests: rewrote `tests/delivery/test_slack_formatter.py` + added `tests/delivery/test_slack_bot_blocks.py` (definitive/conflict/abstain sections + a `_REASONING_MARKERS` leak check).

VERIFY (Batch 3): `tests/delivery/` → **16 passed**. ✓

---

## Batch 4 — Gmail + cross-source merge (PARTIAL DONE)

- Added `tests/pipeline/test_cross_source_merge.py` (hydradb): full pipeline (resolve → extract → gate → load → answer) over Slack + Gmail fixtures; asserts current=Priya, before=Morgan, and evidence spans both sources. PASSED.
- Cross-source was already substantially covered by `test_cross_source_ownership` + `test_source_e2e_cross_source_provenance`.
- **Gmail LIVE is blocked on OAuth** (`GmailAdapter.fetch` raises `NotImplementedError` for live). `scripts/ingest_source.py` already generalizes Slack+Gmail; wiring live Gmail needs `GMAIL_CREDENTIALS_PATH` + a token flow (user resource).

## Batch 6.1 — Benchmark scorer fix (versioned) (DONE)

- `continuum/eval/benchmark/scoring.py`: renamed old logic to `score_answer_v1` (preserved verbatim); added `score_answer_v2` (rejects empty/whitespace got, 1-char answers never pass); `score_answer` = alias to v1 (backward-compat); `score_rows` now uses v2.
- `tests/eval/test_scoring.py` (NEW, 10 tests) — v1 bug documented, v2 guards, golden v1→v2 flips.
- `docs/benchmark-scoring.md` (NEW) — delta table + audit note (`check_answer` has no such bug).
- **Batch 6.2 (500Q same-model/same-scorer comparison) still needs the overnight `make benchmark-full-v1-baseline` run** (Fireworks creds + network + hours — user resource).

---

## Batch 5 — Entity-resolution hardening (DONE)

- Fixed `continuum/entities/scoring.py::_email_username_match` so a dotted Slack handle (`priya.nair`) converges with a Gmail local-part (`priya.nair@x`) — previously `username_base` truncated at the dot and the pair scored REVIEW instead of MERGE. Two-tier now: full-handle (dot-insensitive) then base.
- Added `data/fixtures/phase3/identity-pairs-hard.jsonl` (4 SAME + 4 DIFFERENT + 1 UNCERTAIN) + `tests/eval/test_entity_resolution_hardening.py` (4 tests).
- Result: **false-merge rate 0.0** (same-name/different-org pairs never merge — `guarded_email_match` domain-family guard already held), SAME precision/recall 1.0, UNCERTAIN → REVIEW.
- VERIFY: non-hydradb suite **342 passed**; ER tests 56 passed; hydradb entity_integration 5 passed.

---

## Batch 7 — Knowledge-graph visualization (DONE)

- Added `continuum/query/graph_export.py::export_graph(client, entity_key)` — read-only subgraph export (entities/claims/artifacts/sources as nodes, OWNS/ABOUT/SOURCED_FROM/FROM as edges) using stable business keys.
- Test `tests/pipeline/test_graph_export.py` (hydradb): loads the Morgan→Acme←Priya scenario and asserts nodes/edges/evidence present. PASSED.

## Batch 8 — MCP adapter (DONE)

- Added `continuum/delivery/mcp_adapter.py::ContinuumMCPAdapter` — thin MCP tool catalog (ask/get_current_state/get_history/get_conflicts/get_evidence/resolve_entity/export_graph) + `call()` dispatcher delegating to `QueryService`/`StateQueryAdapter`/`export_graph`. No re-plumbed reasoning.
- Test `tests/delivery/test_mcp_adapter.py` (5 tests). PASSED.

## FINAL — demo story script (DONE, happy path)

- Added `scripts/demo_story.py` — replays the one-story narrative from a clean graph and prints the answer after each turn. The headline live-update transition works: after "Priya is taking over Acme", Continuum answers "Priya owns Acme now".
- Known limitation (Phase 4): "who owned before Priya" and the "Morgan still owns → conflict" step need temporal validity windows that the deterministic extractor only assigns for dated `handing off`/`taking over` phrasings with aligned timestamps. Bare "owns" claims stay open-ended.

---

### Batch 1 — Third-person entity extraction (CODE DONE)
Files changed:
- `continuum/extract/v2/relations.py`
  - `OWNS_VERB_RE` extended with `took over` (past tense).
  - Added `RESPONSIBLE_VERB_RE` (subject + account; object uses `(?!account\b)` so "Redwood account" → "Redwood").
  - Added `HANDED_TO_VERB_RE` (giver group 1, recipient group 2).
  - Wired `RESPONSIBLE_VERB_RE → OWNS` into the `extract_relations` verb loop.
- `continuum/pipeline/source_e2e.py`
  - Imported `HANDED_TO_VERB_RE`, `RESPONSIBLE_VERB_RE` from relations.
  - Added `_relation_person_names(content)` and `_relation_account_names(content)`.
  - Added a third minting pass in `resolve_entities_from_artifacts` that mints person entities from relation-verb subjects/recipients and account entities from responsibility-verb objects. Reuses the SAME regexes as extraction → resolution/extraction always agree. `_accounts_in_text` was NOT touched.
- `tests/pipeline/test_third_person_resolution.py` (NEW, 10 tests) — all 10 pass.

Verified behavior (4 positive + negatives):
- `Morgan owns Acme per the Q4 plan.` → `person:morgan` + `account:acme`, claim `Morgan OWNS Acme` **loadable** (this is the demo-script line).
- `Priya took over Acme.` → `person:priya`, loadable.
- `Sarah is now responsible for the Redwood account.` → `person:sarah` + `account:redwood`, loadable.
- `John handed the project to Maya.` → `person:john` + `person:maya` (no claim — "project" isn't an entity, as intended).
- Negatives: "thanks Morgan!" → not minted; "Acme Health dashboard" → not minted as person.

### VERIFY gate progress (Batch 1)
- New unit tests: 10/10 green. ✓
- **INV-1** `source-e2e` → **20/20**, deterministic across runs. ✓
  - IMPORTANT: extraction precision/recall reads **0.556 / 0.714**. This is **NOT a regression** — the committed `data/metadata/source_e2e_extraction_report.json` is stale (its `commit_sha` is `7995ecf`, not HEAD). I confirmed via `git stash` that the CURRENT baseline (dfc72bd) produces the exact same 9 loadable claims as my change. My change is neutral on E2E.
- **INV-2** non-hydradb suite → **313 passed** (303 baseline + 10 new). ✓
- **INV-3** hydradb suite → **GREEN — all 75 tests pass** (run in chunks: hydradb core 6, slack harness 3, worker+query-core 11, source verticals 11, phase1/2a/2b remainder 44). Note: a single monolithic `-m hydradb` run right after a fresh Docker launch hit transient `EEE..FFF` (startup race); every test passes once the container is warm or run in chunks. ⛔→✓
- **INV-4** `test_incremental_load_preserves_prior_batch_claims` → PASSED. ✓
- **HydraDB integration test (plan §1.3)** → written: `tests/pipeline/test_third_person_integration.py` (worker ingests third-person "Morgan owns Acme." → query "Who owns Acme?" → "Morgan"). PASSED. ✓
- **Demo-script validation from clean graph** → extraction path fully validated (unit + integration + E2E 20/20 all prove "Morgan owns Acme per the Q4 plan." now loads). **Live Slack validation still needs the user's `.env` creds + real workspace** — not automatable here. ⛔(user)

---

## TO DO NEXT (in order)

1. **INV-3**: run the hydradb suite to completion (75 tests, ~needs 15–30 min):
   ```powershell
   $env:PYTHONPATH='.'
   python -m pytest -m hydradb -q -p no:cacheprovider
   ```
   If the store goes stale (the `internal query execution error` on `wipe_for_entities`), do a full reset first:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reset_hydradb.ps1
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_hydradb.ps1
   python -m continuum.hydradb.health
   ```

2. **INV-4** cross-batch history: confirm `test_incremental_load_preserves_prior_batch_claims` passes (part of hydradb suite).

3. **Demo-script validation from clean graph**: reset, then ingest the exact `docs/slack-demo-script.md` seed messages and confirm each expected answer. Key line to prove: `Morgan owns Acme per the Q4 plan.` now loads (it failed before Batch 1). Live Slack needs `.env` creds; fixture mode is fine for the gate.

4. **Optional (plan §1.3)**: add the hydradb-marked integration test that ingests a third-person message via the worker and asserts the right `@continuum who owns Acme?` answer.

5. **Commit Batch 1 as its own PR** (branch off master, e.g. `feature/phase2b-third-person-entities`). Only stage the 3 intended files:
   - `continuum/extract/v2/relations.py`
   - `continuum/pipeline/source_e2e.py`
   - `tests/pipeline/test_third_person_resolution.py`
   - Do NOT commit the noise: `data/metadata/source_e2e_*.json` (stale regen), `data/evals/benchmark-v1/reports/sample-v1/*.json`, `data/metadata/e2e_question_benchmark_test.json` (all modified/generated by running the E2E harness).

6. Then proceed to **Batch 2** (Slack reliability) per the plan.

---

## Environment gotchas (re-learned this session)

- **No `make`** in this shell — run the Makefile's underlying `python`/`powershell` commands directly (see Makefile lines 169–224).
- Use **`python`** (not `python3` — the latter resolves to a different interpreter without `neo4j`).
- Scripts that import `scripts.*` need **`$env:PYTHONPATH='.'`**.
- HydraDB requires a full volume reset when the mounted store goes stale (`internal query execution error`).
- The `data/metadata/source_e2e_*.json` + benchmark sample reports are **tracked but regenerated** by the E2E harness — don't accidentally commit them.

---

## Current uncommitted state (`git status --short`) — POST MERGE TRAIN

All feature code + tests are committed via PRs #19–27. What remains in the
working tree is ONLY the DO-NOT-COMMIT harness noise + docs notes:

```
 M data/evals/benchmark-v1/reports/sample-v1/*.json     <- harness noise (ignore)
 M data/metadata/source_e2e_extraction_report.json       <- harness noise (ignore)
 M data/metadata/source_e2e_failure_taxonomy.json        <- harness noise (ignore)
 M data/metadata/source_e2e_latency.json                 <- harness noise (ignore)
?? data/metadata/e2e_question_benchmark_test.json         <- harness noise (ignore)
?? data/metadata/entity_resolution_eval_hard.json         <- harness noise (ignore)
?? HACKATHON_EXECUTION_PLAN.md                           <- notes (untracked)
?? HACKATHON_EXECUTION_PROGRESS.md                       <- notes (untracked)
```

Safety reference: `snapshot/pre-merge-dfc72bd` (local branch).
