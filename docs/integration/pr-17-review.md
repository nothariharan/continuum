# PR #17 Review

Purpose:
: Event transport/dedup queue (BATCH H) + expanded ER identity-pairs scaffold
  (BATCH G). **Reviewed as two separate concerns as required.**

Branch: `integration/events-queue`
Base: `master`
Dependency: PR #9 (source contract), PR #13 (gateway → queue handoff).
Files:
- `continuum/sources/events.py` (SourceEvent, EventQueue)
- `tests/sources/test_event_queue.py` (1 teammate test + 7 review tests in
  `test_event_queue_extra.py`)
- `scripts/expand_identity_pairs_gold.py`
- `data/labels/phase3-identity-pairs-expanded.jsonl`
- `tests/sources/test_identity_pairs_scaffold.py` (3 review tests)
- `docs/phase3-identity-pairs-scaffold.md` (review addition)
- `Makefile` (`expand-identity-gold` target)
Scope: transport infrastructure + data scaffold.

---

## 17A — Event Queue

**Architecture boundary: correct.** The queue is pure transport:
`SourceEvent` + append-only JSONL + dedup + status marking. It does NOT write
HydraDB, extract claims, resolve entities, or answer questions.

Acceptance chain verified end-to-end (manual harness):

```
webhook (signed Slack event)
  → gateway.handle_http → HMAC valid → handler
  → EventQueue.enqueue → file-backed
  → worker-ready events via load()/mark_processed()
```

Validation:
- unit tests: 8/8 pass (teammate dedup test + 7 review tests).
- duplicate event: enqueue same event twice → second returns False ✓
- replayed event after process restart: fresh queue on same file → False ✓
- different events: both enqueued ✓
- same source/native record, different event_id: **was NOT deduped — fixed** ✓
- same event_id, different native record: deduped ✓
- ordering: preserved across reload ✓
- persistence: file survives restart; `mark_processed` persists status ✓
- malformed line: load raises loudly (no silent skip) ✓

**Defects found and fixed (committed `842dfd2`, documented for teammate):**

1. `dedup_key` included `event_id` (`source|event_id|native_id`), so the same
   source record arriving with a *different* event_id (Slack retries, update
   events) was enqueued twice → could later create duplicate claims. Changed
   to `source|native_id`; event_id dedup retained separately. The gateway's
   per-message `native_id` (`channel:ts`) makes this safe for distinct
   messages.
2. `_seen` was only populated by `load()`; a fresh `EventQueue` (or the
   gateway runner, which never called `load()`) did not dedup against events
   already on disk → replay after restart duplicated. Fixed: `enqueue`
   loads the file once (`_loaded` flag) before checking.

Security:
- credentials: none; queue stores payloads (already-validated Slack events).
- signatures: verification happens in the gateway BEFORE enqueue.
- secrets: audit clean.
- logs: no payload/credential logging.

Data integrity:
- IDs: `event_id` + `dedup_key` both tracked.
- idempotency: at-least-once → deduped on replay; `mark_processed` rewrites
  file idempotently.
- duplicate behavior: covered by the fixes above.
- Concurrency: no file locking — single-process gateway is the current shape;
  noted for the worker milestone.

---

## 17B — ER Gold Scaffold

**Status: SCAFFOLD — NOT validated gold.** Verified data facts:

- 250 rows total.
- Label counts: same 58, different 63, uncertain 129.
- **163 of 250 rows are mechanically duplicated synthetic variants** of the 87
  base pairs (`phase3-identity-pairs.jsonl`), with `-synthetic-N` pair_ids and
  `[synthetic scaffold - replace with labeled pair]` in `note`.
- Script (`expand_identity_pairs_gold.py`) docstring says "scaffold";
  every synthetic row carries an explicit marker.
- No empty mentions; pair_ids unique; schema valid.

Per the plan: "A 'scaffold' is not a validated gold dataset." The labels are
mechanically copied and are NOT human-validated ground truth. The file and
script self-document this; review additionally added:

- `docs/phase3-identity-pairs-scaffold.md` — explicit status, rules (no
  "250 validated pairs" claims, no evaluation against synthetic copies), and
  label distribution.
- `tests/sources/test_identity_pairs_scaffold.py` — enforces 250-row shape,
  label vocabulary, uniqueness, and **that synthetic rows stay visibly
  marked** (guards rule 14 permanently).

Validation:
- data shape/schema: 3/3 tests pass.
- label balance: recorded above; synthetic duplication inflates counts.

Regression:
- previous tests: full non-HydraDB suite — **299 passed, 68 deselected**
  (288 prior + 11 new), 0 failures.
- source→answer gold: untouched.
- benchmark artifacts: byte-identical (restored after suite side effect).

Decision:
    MERGE

Reason:
17A: queue is correct transport infrastructure after the two dedup fixes
(durable file-backed dedup, source|native_id granularity) — the webhook →
queue → worker path from the plan now holds. 17B: the "gold" file is honestly
a scaffold, is self-marking, and is now explicitly documented as such with
permanent guard tests; no evaluation claim depends on it. Both halves are
correct for their true scope; the distinction is preserved in documentation.

Post-merge SHA: `2ba3db003d5d2b2f542dde7d8a6866b3f3e24920` (merge commit);
PR marked MERGED on GitHub (branch head `842dfd2`).
