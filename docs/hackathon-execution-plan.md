# Continuum — Hackathon Execution Plan (post-PR #18)

**Baseline commit:** `dfc72bd` (master, PR #18 merged)
**Author of plan:** review/fix pass after PR #18
**Status of system at baseline:**

| Dimension | State |
|---|---|
| Architecture | Strong — full loop proven |
| Core reasoning | 20/20 synthetic E2E, deterministic |
| Live Slack loop | Proven end-to-end against a real workspace |
| Cross-source | Architecturally proven; live breadth incomplete |
| Reliability | Needs a hardening pass |
| Entity resolution | Biggest technical weakness |
| Benchmark superiority | **Not yet proven** |
| Demo potential | High — if the live-update story lands |

**Guiding principle:** we are past "build architecture." The job now is to make the central claim — *same answer model, better company context, better retrieval/state reconstruction* — **undeniably reliable and measurable**, then prove it on the benchmark. Do **not** add ten new integrations. Optimize for one bulletproof, live-updating company-memory story.

---

## 0. Non-negotiable invariants (must hold after every batch)

These are the regression guardrails. Any batch that breaks one is not "done."

- **INV-1** `make source-e2e` → **20/20**, deterministic across ≥2 runs (identical semantic results).
- **INV-2** Full non-HydraDB suite green: `python -m pytest tests -q -m "not hydradb and not fireworks"` → currently **303 passed**.
- **INV-3** HydraDB suite green: `python -m pytest -m hydradb -q` (worker + harness + phase2b integration incl. `test_incremental_load_preserves_prior_batch_claims`).
- **INV-4** Cross-batch history preserved: two separate `load_claims`/ingest batches with distinct claims → **both** persist (id-collision fix in `continuum/hydradb/claims.py::_stable_id`). Never order logic by node id (ids are non-monotonic hashes now).
- **INV-5** Abstention stays conservative: the system prefers "review"/abstain over a confident wrong answer. No batch may trade this away for a higher raw score.
- **INV-6** No secrets in tree, history, logs, or reports (see Batch 0).

**How to run the full guardrail sweep (the "VERIFY gate" referenced below):**

```bash
# 1. clean graph
make hydradb-reset && make hydradb-up
python -m continuum.hydradb.health          # expect: reachable, ready, authenticated, queryable

# 2. deterministic core
make source-e2e                              # expect 20/20
make source-e2e                              # expect 20/20 identical

# 3. unit + integration
python -m pytest tests -q -m "not hydradb and not fireworks"   # 303+
python -m pytest -m hydradb -q                                 # all green

# 4. live smoke (needs .env creds) — optional per batch, required at Batch-2/3 gates
python scripts/slack_demo_initial_sync.py --mode live --limit 200
```

> **Windows note:** use `python` (not `python3` — that resolves to a different interpreter without `neo4j` installed). `.env` is auto-loaded by `continuum/extract/llm_client.py`; scripts that only touch Slack/HydraDB may need `.env` exported manually (see helper in §Appendix A).

> **HydraDB reset caveat:** a stale mounted store can make `wipe_for_entities`/`DETACH DELETE` throw `internal query execution error`. If that happens, `make hydradb-reset` (full container + volume reset) before `make hydradb-up`. HydraDB rejects label-less `MATCH (n)`; only range/label-scoped deletes work.

---

## Batch sequence (do in order — do not skip the VERIFY gates)

```
CURRENT (dfc72bd)
   → BATCH 0  Credential rotation + secret hygiene        [blocking, do first]
   → BATCH 1  Third-person entity extraction + demo-script truth
   → BATCH 2  Slack loop reliability (crash/replay/idempotency)
   → BATCH 3  Product-grade Slack answer (evidence-rich, no CoT)
   → BATCH 4  Gmail live + cross-source evidence merge
   → BATCH 5  Entity-resolution hardening (identity + negative tests)
   → BATCH 6  Benchmark scorer fix (versioned) + 500Q comparison
   → BATCH 7  Knowledge-graph visualization
   → BATCH 8  MCP / extensibility
   → FINAL    One-story hackathon demo (live update)
```

Each batch is its own PR. Each PR: **review → test → merge → master re-validate** (INV sweep).

---

## BATCH 0 — Credential rotation + secret hygiene *(blocking, ~30 min, no code risk)*

**Why first:** Fireworks key, Slack bot/app tokens, Slack client secret + signing secret were pasted into a chat and live in `.env`. They must be rotated before the repo is shared or the demo is recorded.

**Steps**
1. **Rotate at the source** (invalidates the exposed values):
   - Fireworks dashboard → delete/rotate API key.
   - Slack app → *OAuth & Permissions* → **Reinstall** (rotates `xoxb-`); *Basic Information → App-Level Tokens* → revoke + regenerate (`xapp-`); *Basic Information* → **Regenerate** Client Secret + Signing Secret.
2. Put the new values **only** in `.env` (already git-ignored). Never in chat, code, or committed files.
3. Verify `.env.example` contains **names only** (it does today) — no values.
4. Run the hygiene sweep:

```bash
# secrets not tracked
git ls-files | grep -E '(^|/)\.env$' && echo "LEAK" || echo "ok: .env not tracked"
git check-ignore .env data/ingestion/    # both should print (ignored)

# no secret-shaped strings anywhere in tree
git grep -nE 'xox[bp]-|xapp-|fw_[A-Za-z0-9]{16,}|SLACK_SIGNING_SECRET=[A-Za-z0-9]|-----BEGIN' -- . ':!.env' ':!*.md'

# no secrets in history (full scan)
git log -p | grep -nE 'xox[bp]-[0-9]|xapp-1-|fw_[A-Za-z0-9]{20}' | head

# logs / demo reports don't print credentials
git grep -nE 'FIREWORKS_API_KEY|SLACK_BOT_TOKEN|SLACK_APP_TOKEN' -- 'docs/**' 'data/**'
```

5. Confirm the code never logs tokens: `git grep -n "logger.*TOKEN\|print.*token"` — should be empty.

**Definition of done:** all four checks clean; new creds work (`python -m continuum.hydradb.health` + a live `slack_demo_initial_sync --mode live` succeeds).

**Rollback:** none needed (no code change).

---

## BATCH 1 — Third-person entity extraction + demo-script truth *(highest-priority code change)*

**The bug (confirmed live):** `resolve_entities_from_artifacts` (`continuum/pipeline/source_e2e.py`) mints **person** entities only from structured signals — participants/authors (`_participant_candidates`), `@mentions` (regex `(?<![\w.<])@([A-Za-z0-9_.-]+)`), and emails. A plaintext third-person name in the body ("**Morgan** owns Acme") is extracted into a claim by `OWNS_VERB_RE`/`HANDOFF_PATTERNS`, but then **dropped by the gate** (`scripts/checkpoint_claims.classify_claim`) with *"mention 'Morgan' has no manual resolution."*

Also: accounts are only detected by `_accounts_in_text` in trigger contexts (`OWNS_VERB_RE`: `Name owns X`; `ACCOUNT_NAME_RE`: `taking over/handing off X`). Both the person-subject and the account must resolve for a claim to load.

**Consequence:** `docs/slack-demo-script.md` tells operators to post `"Morgan owns Acme per the Q4 plan."` — which **fails live as written**.

### 1.1 Design (generic, not `Morgan`/`Acme` rules)

Add a **third pass** in `resolve_entities_from_artifacts` that mints person entities from the **subjects of ownership/handoff/responsibility verbs** already recognized by extraction, so extraction and resolution agree.

Patterns to cover (extend the existing `OWNS_VERB_RE` / `HANDOFF_PATTERNS` family, all case-insensitive, `_NAME = [A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)?`):

- `Morgan owns Acme.` (ownership)
- `Priya took over Acme.` / `Priya is taking over Acme.` (handoff)
- `Sarah is now responsible for the Redwood account.` (responsibility → new predicate or map to OWNS)
- `John handed the project to Maya.` (handoff, object-person)

For each matched **person subject** (and, for "handed X to Y", the recipient), mint a person entity via the same path used for @mentions:

```python
key = _person_entity_key(name)          # slug from the display name
entities.setdefault(key, CanonicalEntity(entity_key=key, label="person", name=name))
entities[key].absorb(candidate_from_mention(mention=name, type="person", source=artifact.source))
```

**Critical constraints (protect INV-1 and INV-5):**
- Mint **only** names that are the grammatical subject/object of a recognized relation verb — do **not** mint every capitalized token (that would create garbage entities like "Q4", "Acme Health" as persons and could corrupt the 20/20 fixtures).
- Reuse `_person_entity_key` slugging so a body-name "Morgan" converges with `@morgan` / `morgan@company.com` (same key) — this is what makes cross-signal identity work (feeds Batch 5).
- Keep it **deterministic** (no `set` iteration order; sort candidates).
- Do **not** widen `_accounts_in_text`; if the account still doesn't resolve, that's a separate, explicit follow-up — do not paper over it by auto-accepting unresolved objects (would violate INV-5).

### 1.2 Files to touch
- `continuum/pipeline/source_e2e.py` — new person-minting pass in `resolve_entities_from_artifacts`; possibly a shared helper `_relation_subject_candidates(artifact)` that reuses `OWNS_VERB_RE`/`HANDOFF_PATTERNS`.
- `continuum/extract/v2/relations.py` — if a responsibility verb (`is responsible for`, `now owns`, `handed … to`) needs adding to `OWNS_VERB_RE` / a new predicate map. Keep predicate set within `SUPPORTED_PREDICATES`.
- `docs/slack-demo-script.md` — fix seed phrasing to what actually loads (see Batch 4/Final for the canonical script), OR keep "Morgan owns Acme" **and make it work** (preferred — that's the point of this batch).

### 1.3 Tests (add before/with the change)

New unit tests `tests/pipeline/test_third_person_resolution.py` (no HydraDB — pure extraction):

| Case | Input | Expect |
|---|---|---|
| third-person + ownership | `Morgan owns Acme.` | `person:morgan` minted; claim `Morgan OWNS Acme` **loadable** |
| person + handoff | `Priya took over Acme.` | `person:priya`; loadable |
| responsibility verb | `Sarah is now responsible for the Redwood account.` | `person:sarah` + `account:redwood`; loadable |
| handed-to (two persons) | `John handed the project to Maya.` | `person:john`, `person:maya`; correct subject/object |
| existing known entity | body "Morgan" + author `@morgan` | **same** `person:morgan` key (converges) |
| previously unseen entity | novel name only in body | minted, loadable |
| ambiguous name | `Morgan owns Acme.` + `Morgan owns Beta.` two people? | deterministic; document behavior; prefer single entity unless a distinguishing signal exists |
| cross-signal same person | Slack author + body mention + email of one person | one entity, ≥3 aliases |
| **negative — no relation** | `Great work everyone, thanks Morgan!` | Morgan **not** minted (no ownership/handoff verb) |
| **negative — non-person object** | `Acme Health dashboard` | not minted as a person |

Plus a HydraDB integration test (mark `hydradb`) that ingests a third-person message via the worker and asserts `@continuum who owns Acme?` → the right person.

### 1.4 VERIFY gate (must pass before merge)
1. New unit tests green.
2. **INV-1** `make source-e2e` still 20/20 ×2 (the new pass must not add spurious entities to the gold fixtures — run `make source-e2e` and diff `data/metadata/source_e2e_extraction_report.json` precision/recall; they must not regress).
3. **INV-2/3** full suites green.
4. **Real demo-script validation** from a clean graph: reset HydraDB, run the exact `docs/slack-demo-script.md` seed messages live, and confirm each expected answer. **Do not move on until the real script succeeds from a clean graph.**

**Rollback:** the change is additive (an extra minting pass). If E2E regresses, gate the new pass behind a guard or restrict its verb set; revert the single function.

---

## BATCH 2 — Slack loop reliability *(next real engineering milestone)*

**Goal:** make the loop reliable enough to leave running. Current loop:
`Slack event → HMAC verify (continuum/sources/slack/events.py::verify_slack_signature) → EventQueue (dedup by event_id + source|native_id) → MemoryWorker → extract → ER → HydraDB → @continuum`.

### 2.1 Work items (map to files)
- **Reconnect / Socket-Mode resilience** — `scripts/run_slack_bot.py` (`SocketModeHandler`), `scripts/run_memory_worker.py`, `MemoryWorker.run_forever`. Wrap the poll/consume loop in reconnect-with-backoff; catch transient `slack_sdk`/HTTP errors.
- **Transient Slack API failure + bounded retry** — `continuum/sources/slack/live.py::SlackWebClient._call` (currently a bare `urlopen` that raises `RuntimeError` on `ok=false`). Add: retry with exponential backoff + jitter on 429/5xx/timeout, respect `Retry-After`, cap attempts, surface a typed error after exhaustion.
- **Cursor persistence** — `continuum/sources/lifecycle.py` (`ConnectorSyncLifecycle`, `slack.cursor.json`). Ensure the cursor is written **after** a batch is durably ingested, never before (at-least-once, not at-most-once).
- **Queue durability + crash recovery** — `continuum/sources/events.py::EventQueue` (append-only JSONL). Verify: partial-write tolerance (skip malformed trailing line), `mark_processed` atomicity (currently rewrites the whole file — make it write-temp-then-rename to avoid truncation on crash).
- **Idempotent ingestion** — already: EventQueue dedup + `MemoryWorker._seen_artifacts` + `_stable_id` (Batch-1 fix). Add explicit **poison-event handling**: after N failed attempts, mark `status="failed"` with a reason and move on (don't wedge the queue). Fix the current minor bug where a *skipped* (already-seen) event is marked `"failed"` in `MemoryWorker.process_event` — it should be `"processed"`/`"skipped"`.
- **Failed-event visibility** — a `status` breakdown log/CLI (`scripts/run_memory_worker.py`) + a `data/ingestion/failed-events.jsonl` (git-ignored) for inspection.
- **Graceful shutdown** — `run_forever` should trap SIGINT/SIGTERM, finish the in-flight event, flush cursor, exit clean.

### 2.2 The reliability tests (the ones that matter)

`tests/pipeline/test_memory_worker_reliability.py` (mark `hydradb`):

**T-A — kill/restart/replay idempotency (the headline test):**
```
post message → ingest → (simulate kill: drop worker instance)
→ new MemoryWorker on same queue/artifacts/resolutions paths
→ replay the same event
→ assert exactly ONE artifact for that native_id
→ assert exactly ONE logical claim (no dup node)
→ assert graph state byte-identical to pre-restart
```
**T-B — duplicate + replayed delivery:** enqueue same event twice and a replay with same `native_id` → zero additional claims/artifacts.
**T-C — transient API failure:** mock `SlackWebClient._call` to fail 429 twice then succeed → ingestion completes, no partial/dup state.
**T-D — poison event:** malformed payload / missing `native_id` → marked failed after bounded retries, queue continues, other events unaffected.
**T-E — cursor persistence across restart:** ingest half, restart, ingest rest → all distinct claims present, none reprocessed.
**T-F — succession survives retries:** message A (owner=Morgan), message B (owner=Priya, effective date) → "who owns Acme now?" = Priya, "before?" = Morgan **after** simulated retries/restart.

### 2.3 VERIFY gate
- All reliability tests green.
- INV sweep (1–4) green.
- Live soak (optional but recommended): run `make run-memory-worker` + `make run-slack-bot` against the real workspace for ~15 min, post a handful of messages, confirm no dup claims and stable answers.

**Rollback:** each item is isolated (retry wrapper, atomic queue write, shutdown handler). Revert per-item if a soak reveals regressions.

---

## BATCH 3 — Product-grade Slack answer *(presentation)*

**Goal:** the reply should feel like a product, not "an LLM paragraph." Show **structured evidence**, never internal reasoning/CoT.

**Target format** (rendered as Slack Block Kit):
```
Answer      Priya owns Acme now.
Why         • Slack — ownership announcement
            • Gmail — transition confirmation
            • Linear — ownership update
State       Morgan → Priya  (effective Aug 1)
Confidence  High
```

**Files:** `continuum/delivery/slack_bot.py` (`SlackQueryBot.handle_app_mention` / `handle_slash` — build `blocks`), and the answer envelope from `continuum/benchmark` (`answer()` already returns `value`, `evidence`, `resolution`, `status`, `valid_from/valid_to`, `history`).

**Rules:**
- Map `status`: `definitive` → answer + confidence High; `conflict`/`review` → "Conflicting evidence — needs review" + show both sides; `absent` → honest "I don't have evidence for that."
- `Why` lines come from `evidence[].source` + artifact kind — **no raw model text**, no chain-of-thought.
- `State` from `history` (subject transitions) + `valid_from`. `Confidence` from `status`/`confidence` field.

**Tests:** `tests/delivery/test_slack_bot_blocks.py` — given a canned `answer()` envelope (definitive / conflict / abstain), assert the Block Kit JSON has the right sections and **contains no reasoning strings**. (Pure unit; no Slack, no HydraDB.)

**VERIFY:** INV-2 green; visual check in the real workspace.

**Rollback:** presentation-only; revert `slack_bot.py`.

---

## BATCH 4 — Gmail live + cross-source evidence merge *(only after Slack is reliable)*

**Goal:** answers that **require** multiple sources. Not "we support Gmail" — the test is that one question needs Slack + Gmail (+ Linear) together.

**Files/assets that already exist:** `continuum/sources/gmail/` (adapter, normalize, models), `scripts/ingest_gmail.py`, `GMAIL_CREDENTIALS_PATH`/`GMAIL_TOKEN_PATH` in `.env`, `make ingest-gmail-fixtures`. The `MemoryWorker`/`load_claims` path is source-agnostic already.

**Work items:**
- Wire Gmail through the **same** `ConnectorSyncLifecycle` + `MemoryWorker` path (mirror `slack_demo_initial_sync.py` → a `gmail_demo_initial_sync.py`, or generalize `scripts/ingest_source.py`).
- OAuth: document the one-time `GMAIL_CREDENTIALS_PATH` (client secret json) + token flow; keep tokens git-ignored (`data/ingestion/` already ignored).
- Ensure Gmail artifacts carry the same normalized fields (author/email → person entity, effective dates in body).

**The cross-source test (the point):**
```
Slack:  "Priya is taking over Acme."
Gmail:  "Effective August 1, ownership of Acme transfers from Morgan to Priya."
Linear: "Update ACME-1234 ownership to Priya."
Ask:    "Who owns Acme now, and when did the transition happen?"
Expect: Priya, effective Aug 1, with evidence citing Slack + Gmail (+ Linear).
```
Add as `tests/pipeline/test_cross_source_merge.py` (hydradb) using fixtures, plus a live smoke.

**VERIFY:** INV sweep; cross-source current/historical/conflict all correct; evidence lists ≥2 sources.

**Rollback:** Gmail is additive; disable the Gmail connector to fall back to Slack-only.

---

## BATCH 5 — Entity-resolution hardening *(biggest technical weakness — do before MCP)*

**Goal:** prove identity convergence **and** safe non-merge.

**Must resolve to ONE entity:**
```
Priya · Priya Nair · priya.nair@company.com · @priya · Slack user id · Gmail participant
```
**Must stay separate:**
```
Morgan · morgan@company.com · @morgan   (a different person)
John Smith (org A)  ≠  John Smith (org B)   when evidence doesn't justify merging
```

**Principle (protect INV-5):** **prefer uncertainty over a confident wrong merge.** A wrong merge corrupts the graph and the benchmark claim; an unmerged duplicate is recoverable.

**Files:** `continuum/entities/` (`store.py`, `candidates.py`, resolution logic), `continuum/pipeline/source_e2e.py::resolve_entities_from_artifacts`, `_person_entity_key`. Existing eval harness: `scripts/eval_entity_resolution.py`, `make eval-entity-resolution`, `data/fixtures/phase3/identity-pairs*.jsonl`, `tests/eval/test_identity_pairs_v1.py`.

**Work items:**
- Deterministic key derivation priority: email local-part > username/@handle > name-slug (already the intent — verify and test).
- Merge only on a strong shared signal (same email, same Slack user id, or explicit "X aka Y"). Name-only match across different orgs/domains must **not** merge.
- Emit a `confidence`/`ambiguous` flag on resolutions; ambiguous cases stay separate and are visible.

**Tests:** extend `data/fixtures/phase3/identity-pairs*.jsonl` with the positive convergence set and the **negative** set (same name, different org). Run `make eval-entity-resolution` and add unit assertions in `tests/eval/`. Add precision/recall thresholds and a **zero false-merge** assertion on the negative set.

**VERIFY:** ER eval meets thresholds; **no false merges** on negatives; INV sweep green.

**Rollback:** keep the old resolver behind a flag until the eval passes.

---

## BATCH 6 — Benchmark scorer fix (versioned) + 500Q comparison *(the proof)*

### 6.1 Fix the scorer bug — versioned, not silent
**Confirmed bug:** `continuum/eval/benchmark/scoring.py::score_answer` line 35 — `got_n in gold_n` is `True` when `got_n == ""` (empty string is a substring of everything), so `score_answer("", gold) == True`. This inflated the early result. (`scripts/benchmark_e2e_questions.py::check_answer` is a separate scorer — audit it too.)

**Do NOT silently change it.** Version it:
- Keep `score_answer` as `score_answer_v1` (documented, for reproducing the old number).
- Add `score_answer_v2`: reject empty/whitespace `got` up front (`if not got_n: return False`); require a minimum informative match (empty and 1-char answers never pass); keep abstention symmetry.
- Document the delta in `docs/benchmark-scoring.md`: which questions flip v1→v2 and why.
- **All systems** (BM25/Dense/Hybrid/Continuum) scored with **v2** for the final leaderboard.

**Tests:** `tests/eval/test_scoring.py` — `score_answer_v2("", gold) is False`; `("x", "Priya Nair") is False`; exact/substring/abstention/token-overlap cases; a golden set of v1→v2 flips.

### 6.2 The comparison protocol (same model, same scorer)
Existing harness: `scripts/run_full_v1_baseline.py`, `scripts/build_benchmark_v1.py`, `make benchmark-full-v1-baseline` (bm25/dense/hybrid/continuum), `make analyze-full-v1-baseline`, reports under `data/evals/benchmark-v1/reports/`.

**Protocol — identical for every system:**
```
Question → {system} retrieval / graph reasoning → Context → SAME answer model → SAME scorer (v2)
```
This defends the claim: *"Same underlying answer model. Better company context."* Nobody can say Continuum won because of a better LLM.

**Run (overnight):**
```bash
make build-benchmark-v1                       # or benchmark-foundation-official
make benchmark-full-v1-baseline               # bm25, dense, hybrid, continuum — real answer model, with graph
make analyze-full-v1-baseline
```

### 6.3 Analysis — the differentiated story
Produce the matrix **and** the failure taxonomy (the interesting part):

| System | Retrieval | Answer | Overall |
|---|---|---|---|
| BM25 | | | |
| Dense | | | |
| Hybrid | | | |
| Continuum | | | |

Break losses down by type (reuse `classify_failures` in `source_e2e.py` / `continuum/query/failures.py`): retrieval miss · ER miss · temporal miss · conflict miss · provenance miss · insufficient evidence · answer-gen miss · **safe abstention**.

**Framing:** Continuum need not win every question. The compelling result is *"BM25 retrieves lexical matches but fails on stateful conversational questions; Continuum resolves them via identity + temporal state + conflict + provenance."*

**VERIFY:** scorer tests green; all four systems scored with v2; report numbers reproducible from harness output (no hand-edited metrics); INV sweep green.

**Rollback:** scorer is versioned — v1 remains for reproducing the old number; no data loss.

---

## BATCH 7 — Knowledge-graph visualization

Show the real company graph, not a toy `Morgan → Acme → Priya` line:
```
                     Slack message
                          │ supports
                          ▼
 Morgan ── owned ──► Acme ◄── took over ── Priya
    │                  │                    │
    ▼                  ▼                    ▼
 Gmail thread     Linear issue        Slack user
    └───────────── evidence ──────────────┘
```
Source the graph from HydraDB (`Claim`/`Artifact`/`Source`/entity nodes + relationships). This is the visual of the thesis: *frontier models reason well over supplied context; Continuum constructs the right context.* Read-only over the existing graph — no schema change, low risk. Tests: a query/serialization unit test that the graph export contains the expected nodes/edges/evidence for the demo scenario.

---

## BATCH 8 — MCP / extensibility *(deliberately last)*

Only after Slack + Gmail + benchmark. MCP becomes an **interface** to the already-working memory system, not another architectural distraction. Wrap the existing `answer()` + graph query as an MCP semantic adapter; do not re-plumb reasoning. Tests: adapter contract tests over canned envelopes.

---

## FINAL — One-story hackathon demo (the live-update moment)

Build the demo as **one continuous story**, not a feature tour:

1. **Slack:** someone asks "Does anyone know who owns Acme?" — nobody answers.
2. **Continuum:** `@continuum Who owns Acme now?`
3. **Investigation UI:** `Searching Slack ✓ / Gmail ✓ / Linear ✓ / Querying graph ✓ / Resolving identity ✓ / Resolving time ✓ / Synthesizing evidence ✓`
4. **Answer:** "**Priya owns Acme now.** Morgan owned it before the handoff."
5. **Evidence:** Slack + Gmail + Linear.
6. **Graph:** reveal the company graph.
7. **Live update:** post "Effective tomorrow, ownership moves from Priya to Sarah." → ask again → "**Sarah owns Acme now.**"

Step 7 is the differentiator: **the company's memory changed, and Continuum changed with it.** That is what separates it from "an LLM searching Slack."

**Canonical seed script (must succeed from a clean graph — validate at Batch 1 and re-validate here):**
```
#sales        "Morgan is taking care of the Acme renewal."
#project-acme "Effective August 1, Priya is taking over Acme from Morgan."
#project-acme "Priya confirmed the Acme renewal is now hers."
ask  @continuum Who owns Acme now?            → Priya (evidence)
ask  @continuum Who owned Acme before Priya?  → Morgan (before the Aug 1 handoff)
#sales        "Morgan still owns Acme."       → conflict/review (temporal-aware, not a random pick)
#sales        "Confirmed: Priya owns Acme."   → Priya (definitive)
```
> These phrasings must be validated against the **real** extraction pipeline in Batch 1 (author-as-owner / handoff phrasing, or the new third-person minting). Do not assume — run from a clean graph.

---

## Appendix A — Handy commands & helpers

**Load `.env` in an ad-hoc script (Slack/HydraDB scripts don't auto-load it):**
```python
import os
for line in open(".env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
```

**Clean-graph reset:** `make hydradb-reset && make hydradb-up && python -m continuum.hydradb.health`
**Deterministic core:** `make source-e2e` (×2, expect 20/20)
**Full suites:** `python -m pytest tests -q -m "not hydradb and not fireworks"` then `python -m pytest -m hydradb -q`
**Live Slack ingest:** `python scripts/slack_demo_initial_sync.py --mode live --limit 200`
**Worker + bot:** `make run-memory-worker` / `make run-slack-bot`
**Fireworks smoke:** `make source-e2e-fireworks-smoke` (budget-capped)

## Appendix B — Risk register / "don't break this"

| Risk | Guard |
|---|---|
| New ER pass adds spurious entities → E2E regresses | Mint only relation-verb subjects/objects; diff extraction precision/recall; INV-1 ×2 |
| Ordering logic silently depends on node id | Ids are hash-based/non-monotonic; order only by `valid_from`/`observed_at`; INV-4 test |
| Queue rewrite truncates on crash | Write-temp-then-rename in `EventQueue.mark_processed`; T-A/T-E tests |
| Retry causes duplicate claims | Idempotent `_stable_id` + artifact dedup; T-B/T-C tests |
| Scorer change challenged as cheating | Versioned v1/v2, documented flips, all systems on v2 |
| False entity merge inflates results | Batch-5 negative tests; prefer-uncertainty; zero-false-merge assertion |
| Secrets leak in demo recording | Batch 0 done before any share/record |
| Abstention traded for score | INV-5 explicit; conflict/absent paths tested in Batch 3 |

## Appendix C — Per-batch PR checklist (repeat every batch)

```
[ ] Branch off master (feature/<batch>)
[ ] Code change scoped to the batch's files
[ ] New/updated tests added FIRST (red → green)
[ ] INV-1 make source-e2e 20/20 ×2
[ ] INV-2 non-hydradb suite green
[ ] INV-3 hydradb suite green
[ ] INV-4 cross-batch history test green
[ ] INV-5 abstention still conservative
[ ] INV-6 secret hygiene sweep clean
[ ] Live smoke (Batches 1–4) from a clean graph
[ ] PR: description + review comment documenting what/why + test evidence
[ ] Merge → checkout master → pull → re-run INV sweep FROM master
[ ] Record final master SHA
```
```
```
