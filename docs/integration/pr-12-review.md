# PR #12 Review

Purpose:
: Shared source-ingestion lifecycle (BATCH B) — `initial_sync`,
  `incremental_sync(cursor)`, `fetch_record(native_id)`, `source_health()`,
  `write_artifacts_jsonl()`, plus the unified `ingest_source.py` orchestrator.

Branch: `integration/sync-lifecycle`
Base: `master`
Dependency: PR #9 (SourceConnector contract) + PR #10 (master updated into
  branch; one Makefile conflict resolved by keeping both `ingest-source` and
  `post-stabilization-health` targets).
Files:
- `continuum/sources/lifecycle.py` (110 lines)
- `scripts/ingest_source.py` (62 lines)
- `tests/sources/test_sync_lifecycle.py` (36 lines, 3 tests)
- `continuum/sources/__init__.py` (exports)
- `Makefile` (`ingest-source` target)
Scope: pure transport/normalization orchestration.
Architecture boundary: correct — imports only
  `dataset/artifact` + `sources/{connector,cursor,sync}`. **No HydraDB writes,
  no claim extraction, no entity resolution, no query logic.** (invariant E)

Validation:
- unit tests: 3/3 pass (initial-sync idempotent IDs, incremental no-duplicates,
  source health).
- integration tests: n/a (fixture-backed).
- live smoke: n/a — no live credentials required per plan; fixtures used.
- determinism: manual check — two fresh lifecycle instances produce identical
  artifact IDs for the same records (dsid derived from source + native id).
- failure cases: manual crash/retry simulation verified (see below).

Manual invariant verification (throwaway harness, not committed):

1. `initial_sync` persists cursor after successful processing. ✓
2. Cursor does NOT advance past unprocessed data: connector raised during
   `incremental_sync` → persisted cursor untouched → retry produced zero
   missing/duplicate state. ✓ (at-least-once semantics)
3. Cross-instance dedup: a fresh lifecycle with the persisted cursor returned
   no duplicates of already-ingested records. ✓
4. `source_health()` returns `SyncHealth(source, ok, detail, cursor)`. ✓
5. Deterministic identity: same source record → same Artifact id. ✓

Orchestrator smoke (fixtures): slack → 5 artifacts, gmail → 3 artifacts;
repeat run overwrites initial file, incremental append is cursor-guarded.

Security:
- credentials: read from env only in `--mode live` (`SLACK_BOT_TOKEN`,
  `GMAIL_CREDENTIALS_PATH`); never printed. Fixture mode uses none.
- signatures: n/a.
- secrets: `git diff` audited — none; `.env` remains gitignored.
- logs: only artifact counts and cursor value (a cursor value is opaque, not
  a secret).

Data integrity:
- IDs: stable `artifact_id_from_native(source, native_source_id)` — invariant F.
- provenance: `provenance()` connector method flows into Artifact.metadata.
- idempotency: same-instance `_seen` dedup + persisted cursor + stable IDs.
- duplicate behavior: within process and across processes verified.

Regression:
- previous tests: full non-HydraDB suite post-merge — **267 passed, 68
  deselected** (264 prior + 3 new), 0 failures.
- source→answer gold: untouched (no pipeline/query files changed).
- benchmark artifacts: byte-identical; tracked `sample-v1` reports restored
  after the suite's known regeneration side effect.

Review notes:
- `fetch_record` falls back to a 10k-record scan when the adapter has no
  `fetch_record` (current Slack/Gmail adapters do not implement it). Fine for
  fixtures; a real per-record fetch should be added with live adapters.
- Cursor file write is not atomic (`Path.write_text`); a crash mid-write could
  corrupt the cursor JSON and require deleting it and re-syncing. Minor
  robustness gap, acceptable at this stage; noted for the live adapters batch.
- Hygiene: `data/ingestion/` outputs are tracked in git (pre-existing from
  #9); smoke-run modifications were restored to HEAD and no cursor files were
  committed.

Decision:
    MERGE

Reason:
Lifecycle is exactly the shared ingestion abstraction the train needs: cursor
persistence, at-least-once retryability, deterministic artifact identity, and
a hard boundary at canonical Artifacts (no graph/extraction/query coupling).
All invariants A–F from the plan were verified by test or manual harness.

Post-merge SHA: `09425204749fbd888c6e5865f6e335e44a83c3b8` (merge commit);
PR marked MERGED on GitHub (merge commit `6631cb8` recorded as PR head).
