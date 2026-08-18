# PR #15 Review

Purpose:
: Slack query bot (BATCH F) — mention/slash handling, Block Kit formatter,
  Socket Mode dev runner. Answers via the QueryService seam.

Branch: `integration/slack-bot` (originally stacked on `integration/query-api`)
Base: `master` (content-wise; see merge note)
Dependency: PR #14 (QueryService seam). Branch was updated against post-#14
  master before merge (one Makefile conflict resolved — all targets kept).
Files:
- `continuum/delivery/slack_bot.py` (91), `continuum/delivery/slack_formatter.py` (52)
- `scripts/run_slack_bot.py` (68)
- `tests/delivery/test_slack_formatter.py` (2 teammate + 2 review tests)
- `tests/delivery/test_slack_bot.py` (3 review tests, new file)
- `Makefile` (`run-slack-bot` target)
Scope: delivery transport + formatting only.
Architecture boundary: correct —
  `@continuum question → extract_question → QueryService.ask() → existing
  reasoning → formatter → answer`. **No duplicated graph/query logic**
  (stop condition #10 verified: the bot never touches HydraDB queries or
  reasoning; it calls the same `QueryService.ask()` as the HTTP API).

Validation:
- unit tests: 9/9 delivery tests pass (formatter: definitive, abstention,
  conflict, historical; bot: mention stripping, single-post + delegation,
  empty-question guidance).
- integration tests: n/a (HydraDB not required for transport).
- live smoke: **not run** — no `SLACK_BOT_TOKEN`/`SLACK_APP_TOKEN` on this
  machine. Socket Mode correctly labeled as dev mode; production Events path
  still pending (per plan, no production-readiness claim made).
- determinism: formatting is pure; verified outputs stable across calls.
- failure cases (manual harness):
  - mention stripping handles 1+ mentions and plain text ✓
  - empty question → guidance payload, zero query calls ✓
  - conflict → "Multiple conflicting claims — review required" ✓
  - historical ("who owned Acme before?") → "Previous holder: Morgan" + evidence ✓
  - abstention → "Unknown — insufficient evidence" ✓
  - evidence renders up to 5 items with source + date ✓

Security:
- credentials: `SLACK_BOT_TOKEN` from env, sent only in the Authorization
  header; errors raised without echoing the token; runner prints no secrets.
- signatures: n/a (bot posts via Web API; the Events gateway handles inbound).
- secrets: audit clean; `.env.example` placeholders only.
- logs: bot failures logged by slack-bolt without payload dumping.

Data integrity:
- IDs: n/a (stateless transport; `thread_ts` preserved for threaded replies).
- provenance: evidence chain passes through formatter untouched.
- idempotency: n/a.
- duplicate behavior: n/a (dedup lives in the ingestion side).

Regression:
- previous tests: full non-HydraDB suite — **284 passed, 68 deselected**
  (277 prior + 7 new), 0 failures.
- source→answer gold: untouched.
- benchmark artifacts: byte-identical (restored after suite side effect).

Review notes:
- **Defect found and fixed (committed `2dc9f3f`, documented for teammate):**
  the Socket Mode runner called `say()` after `handle_app_mention`/`handle_slash`,
  but those already post via the bot's default `chat.postMessage` path → every
  mention would have produced **two messages**. Fix: `build_bot_from_env`
  accepts an injectable `post_message`; the runner injects a no-op poster so
  `say()` is the single delivery path in Socket Mode. Regression test
  `test_handle_app_mention_posts_once_and_delegates` locks the single-post
  invariant.
- **Merge note:** GitHub merged the PR against its stale base
  (`integration/query-api`), creating merge commit `df5f55f` on that branch.
  Master already contained the full PR #15 content via the reviewed local
  merge (`546c141`); `git diff df5f55f master` is empty (trees identical).
  No content loss; the stale-base branch is already merged and archived.
- Bot class kept as teammate wrote it; only the injectable poster + runner
  wiring changed.

Decision:
    MERGE

Reason:
Pure transport with a single reasoning path (QueryService.ask()), readable
evidence-backed formatting, safe abstention/conflict rendering, and no
duplicated logic. The double-post defect would have broken the real demo
("@continuum who owns Acme?" posting twice); it was caught and fixed with a
regression test before merge.

Post-merge SHA: `546c14160072cd860900a5167c2dcd78dc76f82a` (merge commit);
PR marked MERGED on GitHub (branch head `2dc9f3f`).
