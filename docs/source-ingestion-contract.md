# Source Ingestion Contract

Status: **PROPOSED v1** — requires founder sign-off before merge.

This document defines the boundary between **source adapters** (teammate-owned)
and **Continuum ingestion** (founder-owned graph/extraction). Adapters terminate
at the canonical `Artifact` defined in [`continuum/dataset/artifact.py`](../continuum/dataset/artifact.py).

> **Rule:** Once an artifact crosses this boundary, source-specific code stops.

See also: [`contract-v1.md`](contract-v1.md) (Mention/Claim contract), [`phase-2-dataset.md`](phase-2-dataset.md) (benchmark normalization).

---

## Pipeline

```
Slack / Gmail / GitHub / Jira
        ↓
   SourceAdapter (continuum/sources/)
        ↓
   Canonical Artifact
        ↓
   extraction → claims → entity resolution → HydraDB → query
```

Adapters must **not** write to HydraDB, resolve entities, or emit claims directly.

---

## Field mapping

| Founder term | Artifact field | Notes |
|---|---|---|
| `artifact_id` | `id` | `dsid_<32-hex>`, stable across re-ingestion |
| `source` | `source` | `slack`, `gmail`, `github`, `jira`, … |
| `source_id` | `source_id` | **Native upstream ID** (e.g. `C07ABC:1728291000.123456`) |
| `source_type` | `type` | e.g. `slack_message`, `gmail_message` |
| `title` | `title` | Short label (channel/subject/first line) |
| `content` | `content` | Full text for extraction |
| `author` | `author` | Primary author display name or email |
| `timestamp` | `timestamp` | ISO-8601 when the record was created/sent |
| `participants` | `metadata.participants` | Raw identities; **not pre-resolved** |
| `thread_id` | `metadata.thread_id` | Thread/conversation identifier |
| `source_url` | `metadata.source_url` | Permalink when available |
| `ingested_at` | `metadata.ingested_at` | When Continuum ingested the record |
| (other provenance) | `metadata.*` | Source-specific; see per-source tables below |

### ID generation (live sources)

```python
id = f"dsid_{sha256(source + '|' + native_source_id)[:32]}"
source_id = native_source_id  # NOT the dsid hash
```

Benchmark files (`Artifact.from_raw`) keep legacy semantics where `source_id`
is the filename dsid hex. Live ingestion uses `Artifact.from_source_record()`.

---

## SourceConnector interface

Defined in [`continuum/sources/connector.py`](../continuum/sources/connector.py):

| Method | Purpose |
|---|---|
| `authenticate()` | Validate credentials or fixture config |
| `fetch(cursor, limit)` | Return raw records + next cursor |
| `normalize(raw)` | Raw → `Artifact` |
| `cursor(raw)` | Derive sync position from latest record |
| `provenance(raw)` | Provenance dict merged into `metadata` |

Incremental sync uses [`SyncCursor`](../continuum/sources/cursor.py):
`{source, value, last_sync_at}`.

---

## Required metadata per source

### Slack

| Key | Required | Description |
|---|---|---|
| `message_id` | yes | Slack message `ts` |
| `channel_id` | yes | Channel ID |
| `channel_name` | no | Human-readable channel name |
| `thread_id` | no | Parent `thread_ts` if in thread |
| `workspace_id` | no | Slack team/workspace ID |
| `author_user_id` | no | Slack user ID |
| `author_display_name` | no | Display name |
| `participants` | no | List of `{user_id, display_name}` |
| `mentions` | no | Raw `@handles` found in text |
| `links` | no | URLs in message |
| `reply_count` | no | Thread reply count |
| `source_url` | no | Permalink |

### Gmail

| Key | Required | Description |
|---|---|---|
| `message_id` | yes | Gmail message ID |
| `thread_id` | yes | Gmail thread ID |
| `participants` | no | From/To/Cc emails (raw) |
| `subject` | no | Email subject (also in `title`) |
| `source_url` | no | Gmail web URL |

### GitHub / Jira

| Key | Required | Description |
|---|---|---|
| `message_id` | yes | PR/issue/comment identifier |
| `repository` / `project` | no | Repo or Jira project key |
| `source_url` | no | Web permalink |

---

## JSONL interchange

Same format as Phase 2A sample (`artifact_to_dict()`):

```json
{
  "id": "dsid_abc...",
  "source": "slack",
  "source_id": "C07ABC:1728291000.123456",
  "type": "slack_message",
  "author": "Sarah Chen",
  "timestamp": "2026-07-28T14:30:00+00:00",
  "title": "#product-handoffs",
  "content": "...",
  "metadata": {
    "message_id": "1728291000.123456",
    "channel_id": "C07ABC",
    "thread_id": "1728290000.000000",
    "participants": [{"user_id": "U01", "display_name": "Sarah Chen"}],
    "source_url": "https://workspace.slack.com/archives/C07ABC/p1728291000123456",
    "ingested_at": "2026-08-17T10:00:00+00:00"
  }
}
```

Load with existing scripts: `dataset_load_hydradb.py` (artifact nodes only).

Extract with: `extract_mentions.py` / `extract_claims.py` on JSONL artifacts.

---

## Founder review checklist (Gate)

Before merging PR #9, confirm:

- [ ] `source_id` stores native upstream ID (not dsid hash) for live records
- [ ] `id` derivation is stable and idempotent
- [ ] Provenance fields live in `metadata`, not a parallel schema
- [ ] Participants are raw identities (no entity resolution in adapters)
- [ ] JSONL interchange matches existing HydraDB artifact load

---

## Incremental sync

Use [`continuum/sources/sync.py`](../continuum/sources/sync.py) to persist cursors:

```bash
python3 scripts/ingest_slack.py --mode fixtures --incremental --limit 2
python3 scripts/ingest_gmail.py --mode fixtures --incremental --limit 1
```

Cursor file shape: `{source, value, last_sync_at}`.

## Webhook interface (stub)

[`continuum/sources/webhook.py`](../continuum/sources/webhook.py) defines `SourceEvent`
and `WebhookHandler` protocols. Live webhook wiring is deferred; incremental
`fetch(cursor)` is the current sync path.

- Entity resolution / canonical entity IDs
- Claim or mention extraction
- HydraDB graph writes (beyond artifact JSONL handoff)
- Benchmark modifications
- MCP / UI
