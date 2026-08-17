# Slack Ingestion Checkpoint — Founder Handoff

Status: **ready for joint E2E validation**

This checkpoint delivers Slack-sourced canonical Artifacts for the founder to run
through the existing extraction → entity resolution → HydraDB → query pipeline.

## What was delivered

| Artifact | Path |
|---|---|
| Slack fixtures (4 files, 5 messages) | [`data/fixtures/sources/slack/`](../data/fixtures/sources/slack/) |
| Normalized JSONL output | [`data/ingestion/slack-artifacts.jsonl`](../data/ingestion/slack-artifacts.jsonl) |
| Ingestion contract | [`docs/source-ingestion-contract.md`](source-ingestion-contract.md) |
| Adapter code | [`continuum/sources/slack/`](../continuum/sources/slack/) |

## How to reproduce

```bash
make ingest-slack-fixtures
# or:
PYTHONPATH=. python3 scripts/ingest_slack.py --mode fixtures
```

Expected output: **5 artifacts** written to `data/ingestion/slack-artifacts.jsonl`.

## Fixture → scenario mapping

| Fixture file | Scenario | Expected content |
|---|---|---|
| `single_message.json` | CedarBank handoff announcement | Maya Patel → Camila Reyes handoff, ENG-5842 |
| `thread_with_replies.json` | Thread with participants | Jonas Weber + Sarah Chen on payments dependency |
| `mentions_and_links.json` | @mentions + external links | Soham mention, Linear ENG-9001 link |
| `cross_reference_handoff.json` | Two-message ownership transition | Maya still owns CedarBank → Camila takes over July 28 |

## Artifact IDs (stable — idempotent re-ingestion)

Run this to list ids after ingest:

```bash
python3 -c "
import json
from pathlib import Path
for line in Path('data/ingestion/slack-artifacts.jsonl').read_text().splitlines():
    row = json.loads(line)
    print(row['id'], row['source_id'], row['title'])
"
```

## Founder validation steps

1. Load artifacts (optional HydraDB artifact nodes):
   ```bash
   # Convert JSONL to sample load if needed, or point extraction at JSONL
   ```
2. Extract mentions/claims:
   ```bash
   # Founder pipeline — read data/ingestion/slack-artifacts.jsonl as Artifact input
   ```
3. Manual entity resolution for any new mentions
4. Load claims into HydraDB
5. Query state + provenance for CedarBank ownership handoff scenario
6. Confirm provenance traces back to `metadata.source_url` / Slack message

## Joint success criterion

> A real Slack conversation enters Continuum, survives normalization, has its
> people resolved, becomes claims and graph state, participates in
> temporal/conflict reasoning, and produces an answer with provenance back to
> the original message.

**Recommended first test question:** Who owns CedarBank as of July 28, and what
Slack evidence supports the answer?

## Incremental sync (optional)

```bash
PYTHONPATH=. python3 scripts/ingest_slack.py --mode fixtures --incremental \
  --cursor data/ingestion/slack.cursor.json --limit 2
```

Cursor format: `{source, value, last_sync_at}` — see [`continuum/sources/sync.py`](../continuum/sources/sync.py).

## Out of scope for this checkpoint

- Live Slack API (stub raises `NotImplementedError`; use fixtures)
- Gmail/GitHub/Jira (separate adapters on `integration/gmail-adapter`)
- Benchmark runs
