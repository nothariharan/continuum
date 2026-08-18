# PR #13 Review

Purpose:
: Live Slack ingestion (BATCH C) — Web API client, OAuth/credential helpers,
  Events API gateway (signature validation, fast ACK, enqueue-only handoff),
  and a runnable gateway server.

Branch: `integration/slack-live`
Base: `master`
Dependency: PR #9 (adapter/normalize), PR #12 (sync lifecycle for consumption).
  **Forward dependency found:** `scripts/run_slack_events_gateway.py` imports
  `continuum.sources.events` (`EventQueue`, `SourceEvent`) which is added by
  PR #17. The gateway module itself is standalone and fully tested; the runner
  script only becomes runnable after #17 merges. Verified at review time and
  will be exercised in the Phase 10 cross-PR test.
Files:
- `continuum/sources/slack/oauth.py` (36), `live.py` (80), `events.py` (79),
  `adapter.py` (+64)
- `scripts/run_slack_events_gateway.py` (65)
- `tests/sources/test_slack_events.py` (2 teammate tests + 6 added in review)
- `.env.example` (documents SLACK_* vars), `Makefile` (`run-slack-events`)
Scope: transport only.
Architecture boundary: correct —
  `event → signature verify → fast ACK → enqueue (handler) → worker → sync
  lifecycle`. Handler does **only queue enqueue**; no extraction, no HydraDB,
  no entity resolution in the webhook path. (invariant "no heavy sync work in
  webhook")

Validation:
- unit tests: 8/8 pass (signature, url_verification, valid event, bad
  signature, stale timestamp, missing timestamp header, malformed payload,
  duplicate event).
- integration tests: n/a (no live credentials available on this machine).
- live smoke: **not run** — `SLACK_BOT_TOKEN`/`SLACK_SIGNING_SECRET` not
  present in env. Required credentials documented in `.env.example`.
- determinism: fixture path unchanged (61 sources tests still pass).
- failure cases (manual harness):
  - valid signed event → 200, handler invoked once ✓
  - wrong signature → 401 ✓ (before any payload parsing)
  - stale timestamp (>300 s) → 401 ✓
  - 299 s-old timestamp → accepted ✓ (window boundary)
  - duplicate event_id → 200 `{deduped: true}`, handler NOT re-invoked ✓
  - missing timestamp header → **was ValueError/500 — fixed to 401** in review
  - malformed JSON with valid signature → **was unhandled JSONDecodeError/500
    — fixed to 400** in review

Security:
- credentials: read from env only; `health_detail()` reports booleans, never
  values; nothing printed/logged (gateway `log_message` suppressed).
- signatures: Slack v0 HMAC-SHA256 + timestamp freshness + `compare_digest` ✓.
- secrets: `.env.example` has empty placeholders only; `git diff` audited.
- logs: gateway access logs disabled by default; no credential material.

Data integrity:
- IDs: native `ts`/channel preserved; `native_source_id` flows through the
  same `normalize` path as fixtures; `fetch_record` implemented on the adapter.
- provenance: workspace id/subdomain captured per message via `auth_test`.
- idempotency: in-process `_seen` dedup by `event_id`/`client_msg_id`/`ts`;
  cross-restart dedup is deferred to the PR #17 EventQueue (documented).
- duplicate behavior: deduped events are not enqueued (no duplicate claims).

Regression:
- previous tests: full non-HydraDB suite on branch — **275 passed, 68
  deselected** (267 prior + 8 new), 0 failures.
- source→answer gold: untouched.
- benchmark artifacts: byte-identical (restored after suite side effect).

Review notes:
- Two defensive fixes added by founder in review gate (committed `f5354d6`,
  documented for teammate): `verify_slack_signature` returns False on
  non-numeric timestamp; `handle_http` returns 400 on malformed JSON. Plus 6
  edge-case tests in `test_slack_events.py`. Without these, a headerless or
  malformed request would produce a 500 (retryable) instead of a clean 401/400.
- `run_slack_events_gateway.py` forward-imports PR #17's `continuum.sources.events`;
  `make run-slack-events` is inert until #17 lands. Not blocking: the gateway
  module and tests are self-contained.
- In-memory dedup resets on restart — acceptable because the EventQueue +
  stable artifact IDs provide the durable layer (to be verified in Phase 10).

Decision:
    MERGE

Reason:
Signature validation, freshness, fast ACK, and enqueue-only handoff satisfy the
BATCH C architecture. No synchronous pipeline work in the webhook. Defensive
gaps found in review were fixed and tested. The one forward reference (event
queue) is to the next planned teammate PR and is exercised end-to-end in the
Phase 10 cross-PR test rather than blocking this batch.

Post-merge SHA: `2811636ea2b137346bb13cad4306cef9227d2ecc` (merge commit);
PR marked MERGED on GitHub (branch head `f5354d6`).
