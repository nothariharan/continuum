# Phase: Source → Continuum Core Integration Review (PR #9)

**Status:** APPROVED — vertical proven end-to-end against a live HydraDB.
**PR:** #9 `feat(sources): fixtures-first source ingestion contract and Slack/Gmail adapters`
**Branch:** `integration/source-contract`
**Review branch:** `feature/source-core-integration`

---

## What PR #9 adds

A fixtures-first source-ingestion layer (`continuum/sources/`) that terminates
at the canonical `Artifact`:

- `SourceConnector` protocol: `authenticate() / fetch(cursor, limit) /
  normalize(raw) / cursor(raw) / provenance(raw)`
- `SyncCursor` + `sync.py` cursor persistence (incremental sync scaffolding)
- **Slack adapter**: thread-aware fixtures (`SlackThreadFixture`), users,
  replies, mentions, links, permalinks
- **Gmail adapter**: API-shaped + RFC822 fixture parsing, participants,
  threads, source URLs
- `Artifact.from_source_record()`: stable `dsid_<sha256(source|native_id)>`,
  native ID preserved in `source_id`
- `data/fixtures/sources/{slack,gmail}/`, normalized JSONL handoff
  (`data/ingestion/*.jsonl`), ingest scripts, Makefile targets, docs

## SourceConnector boundary

Source-specific code stops at `Artifact`. Verified:

- `Artifact.from_source_record` produces contract-compliant `dsid_<32hex>` ids
- No source-specific branch in `continuum/query/*` or `benchmark/pipeline.py`
  (a dedicated test greps the query core for `if source == slack/gmail/...`)
- Adapters do **not** resolve identities, write to HydraDB, or emit claims —
  they emit evidence; the shared resolver/loader decides identity

## Canonical Artifact mapping

| Field | Source value | Stored |
|---|---|---|
| `id` | `sha256(source\|native_id)[:32]` | `dsid_<32hex>` (idempotent) |
| `source_id` | native upstream ID | Slack `channel:ts`; Gmail `message_id` |
| `timestamp` | Slack ts / Gmail Date | ISO-8601 |
| `title` | Slack `#channel` / Gmail subject | yes |
| `content` | conversational thread text | yes |
| `thread_id` | Slack `thread_ts` / Gmail `threadId` | `metadata.thread_id` |
| participants | raw identities (not resolved) | `metadata.participants` |
| `source_url` | permalink | `metadata.source_url` |

Native IDs are preserved and non-destructive (never replaced by generated ids).

## Thread / context quality

- **Slack**: `normalize_slack_message` embeds root + replies into the content
  (`#channel\nAuthor: text\n  Reply: text`) so "I'll take it" keeps its
  thread context. `metadata` carries `reply_count`, participants, mentions.
- **Gmail**: `build_content` emits `From/To/Cc/Date/Subject` + body; thread_id
  is preserved and shared across messages in a thread.

## Provenance model

Every artifact retains `source_url`, `thread_id`, `message_id`, author,
participants, native id — the evidence trail survives normalization. The
graph path resolves `Claim → SOURCED_FROM → Artifact → FROM → Source` and the
query envelope's `evidence[]` exposes source + artifact + observed time back
to the original source message.

## JSONL handoff

Deterministic: fixture run twice → identical artifact IDs and canonical
content; only the intentionally-nondeterministic `ingested_at` differs.
Verified by `scripts/verify_pr9_determinism.py`.

## Cross-source behavior (proven)

The same core answers from either source or a combination:

- **Slack temporal handoff**: "Who owns Acme now?" → Priya; "Who owned Acme
  before Priya?" → Morgan; provenance points to the Slack artifacts.
- **Gmail**: "Who owns Acme now?" → Soham with Gmail provenance.
- **Cross-source**: current owner from Slack, previous owner from Gmail;
  evidence identifies both artifacts. No source-specific query path.
- **Conflict**: contradictory same-day claims → `conflict` (never an
  arbitrary pick).
- **Entity resolution**: Slack `@soham` and Gmail `soham@company.com` both
  resolve to `person:soham` through the shared resolution map (adapters
  emit evidence only).

## Live API readiness

`from_source_record()` accepts real native IDs; `authenticate/fetch/cursor`
are present; live paths raise `NotImplementedError` at a clean seam. A live
Slack/Gmail connector later slots in behind the same `SourceConnector`
protocol with no core-query rewrite.

## Integration fixes (found during this review)

1. `hydradb/claims.load_claims`: coerce missing fixture-artifact fields
   (`title`, `timestamp`) — the HydraDB query engine rejects UNWIND rows
   missing referenced fields (this had silently broken `load_phase2b_claims.py`).
2. State resolvers are now **claim-faithful**: `resolve_state`,
   `resolve_state_on`, history, and `before` derive validity from Claim nodes
   (which preserve exact `valid_from/valid_to`), not the predicate edge whose
   validity collapses when multiple claims share a subject→object pair.
3. `resolve_conflict_state`: superseded status requires **strictly distinct**
   observation times; otherwise `conflict`/`review` — never an arbitrary pick.
4. Temporal anchors may be person names ("before Priya" → previous holder)
   and event anchors resolve to the latest dated artifact (Python-side match,
   since the engine WHERE rejects `toLower`/`CONTAINS`).
5. `artifact_to_claim_fixture` / `artifact_source_fixture`: the glue that maps
   source `Artifact` → `load_claims` shape, with display source names.

## Remaining limitations

- **Event-anchor matching** (`anchor_date`) is global over artifact titles and
  case-sensitive substring-based; it is correct in a clean graph but should
  become scope-aware (prefer artifacts connected to the queried entity) when
  the corpus is large.
- **Compound questions** ("who owns X now, and who owned it before?") are not
  yet split into multiple QueryContext clauses — ask the clauses separately
  for now.
- **Live connectors** (OAuth/webhooks/incremental sync) are intentionally not
  wired — this PR is fixtures-first.
- **Extraction** of claims from source content is still the teammate's
  deterministic extractor; the vertical tests hand-write claims referencing
  source artifacts.
- Idempotency is at the artifact-ID level (stable ids + `MERGE`); a full
  upsert-persistence model is not implemented (documented, not silently added).

## Vertical status

| Step | Status |
|---|---|
| Slack fixture → Artifact | **PASS** |
| Gmail fixture → Artifact | **PASS** |
| Artifact → claims (fixture claims reference artifacts) | **PASS** |
| claims → entities (shared resolution map) | **PASS** |
| entities → graph (load_claims → HydraDB) | **PASS** |
| graph → QueryContext (decompose) | **PASS** |
| QueryContext → state (temporal/current) | **PASS** |
| QueryContext → conflict | **PASS** |
| state → answer | **PASS** |
| answer → source provenance (Slack/Gmail) | **PASS** |

## Tests

- Pure (no HydraDB): 229 non-hydradb tests green (source-boundary, query-core,
  eval, phase2b, phase1/2a)
- HydraDB-gated (run against live HydraDB): 25 green across
  `tests/hydradb`, `test_semantic_interface`, `test_benchmark_adapter`,
  `test_query_core_integration`, `test_source_core_integration`

## Merge decision

All 16 Phase-21 acceptance criteria pass. **Recommend: merge.**