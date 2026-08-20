# Golden-Path Demo — Runbook

One real company-memory story, end to end:

> Slack (Morgan owns Acme) → Gmail (transfer to Priya, Aug 3) → Continuum ingests
> both → entity resolution → temporal state → graph updates → the same question
> gets a new answer, with the previous state still queryable — proven identically
> across Web, Slack, Graph, and MCP.

Everything runs through the **canonical pipeline** (resolve → extract → gate →
load). Nothing edits the graph by hand; nothing is faked in the UI.

## Files

- `scenario.json` — the canonical truth (entities, events, dates, messages,
  expected answers). **Do not change this the morning of the demo.**
- `../../scripts/demo_golden_path.py` — reusable engine (importable, no side effects).
- `../../scripts/demo_console.py` — the operator console (commands below).

## Prerequisites

```bash
make hydradb-up        # start HydraDB (needs Docker Desktop running)
make demo-health       # must be GREEN before you present
```

`demo-health` checks: scenario loads, query/MCP layer importable, HydraDB
reachable, graph readable, QueryService + evidence readable. Optional Slack/Gmail
credentials are informational only — the demo is fully deterministic without them.

## Commands

| Command | What it does |
|---|---|
| `make demo-health` | Pre-demo health board (green/red) |
| `make demo-reset` | Scoped clear of just the demo entities (Acme/Morgan/Priya) |
| `make demo-seed` | Seed the initial Slack state (Morgan owns Acme) |
| `make demo-apply EVENT=gmail-transition` | Ingest Gmail transfer (→ Priya, Aug 3) |
| `make demo-apply EVENT=gmail-aug5` | Ingest the Aug-5 correction |
| `make demo-apply EVENT=slack-conflict` | Ingest a contradicting Slack message |
| `make demo-ask Q="Who owns Acme now?"` | Ask via the canonical query layer |
| `make demo-status` | Current owner + graph summary + history |
| `make demo-run` | The full scripted narrative, printed |
| `make demo-gates` | Acceptance gates 1-8, run 3× for determinism |
| `make demo-parity` | Prove Web == Slack == MCP == Graph read the same state |
| `make demo-recovery` | Gate 9 — memory survives a connection/process restart |

(Direct form: `PYTHONPATH=. python scripts/demo_console.py <cmd>`.)

## The frozen demo sequence (what to click/say)

1. `make demo-reset && make demo-seed`
2. **Ask:** `make demo-ask Q="Who owns Acme?"` → **Morgan** (evidence: Slack)
3. Show the Slack evidence.
4. **Apply Gmail:** `make demo-apply EVENT=gmail-transition`
5. Show the graph change: Morgan → Acme → Priya.
6. **Ask again:** `make demo-ask Q="Who owns Acme now?"` → **Priya**, effective **Aug 3**, evidence **Slack + Gmail**
7. **Ask history:** `make demo-ask Q="Who owned Acme before Priya?"` → **Morgan**
8. **Live update:** `make demo-apply EVENT=gmail-aug5` → ask again → still **Priya**, now effective **Aug 5**; "before" still **Morgan**.
9. **Slack parity:** `@continuum who owns Acme?` (needs the running bot) → same answer.
10. **MCP parity:** shown in `make demo-status` / `make demo-run` last line.

Or just run the whole thing: `make demo-run`.

## Acceptance gates (`make demo-gates`)

1. Initial memory — Slack → Morgan.
2. Cross-source update — Gmail → Priya (Aug 3), no manual graph edit.
3. Temporal memory — "before Priya" still returns Morgan.
4. Evidence — grounded in real Slack + Gmail artifacts.
5. Graph — reflects canonical state (Acme, Morgan, Priya).
6. MCP parity — MCP current owner == web current owner.
7. Repeatable — reset→seed→transition→query is identical across 3 runs.
8. Live update — Aug 5 supersedes Aug 3.

## Plan B (fully offline)

The console already IS the offline path: ingestion is in-process from
`scenario.json` through the real pipeline — **no Slack/Gmail network calls**. If
live OAuth breaks, the exact same story, graph, evidence, and answers run from
fixtures. Only the source *transport* differs; the memory semantics are identical.

## Web / Slack

- **Web:** run the query API (`make run-query-api`) + the web app (`make web-dev`).
  The UI reads the same `/v1/*` endpoints, so it shows this state live.
- **Slack:** run the bot (`make run-slack-bot`); `@continuum who owns Acme?` uses
  the same `QueryService` + formatter — the answer matches the web and MCP.
