# Slack Company Memory Demo — Operator Script

Reproducible steps for the live demo workspace (Batch B matrix B6–B16).

## Prerequisites

- HydraDB running (`make hydradb-up` or Docker on ports in `.env`)
- `.env` with `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, optional `SLACK_CHANNEL_IDS`
- Python deps: `pip install -e ".[delivery]"`

## 1. Initial ingest

```bash
make slack-demo-sync          # fixtures mode (CI/dev)
# or live:
python3 scripts/slack_demo_initial_sync.py --mode live --limit 200
```

## 2. Start memory worker + bot (two terminals)

```bash
make run-memory-worker        # terminal A — polls EventQueue → graph
make run-slack-bot            # terminal B — @continuum queries
```

For live Slack events without ngrok, post messages in the workspace; enqueue
manually for dev:

```bash
# After posting in Slack, append to data/ingestion/slack-events.jsonl or use gateway
make run-slack-events         # optional HTTP gateway if Request URL configured
```

## 3. Seed messages (human — post in demo workspace)

| Channel | Message |
|---------|---------|
| `#sales` | Morgan owns Acme per the Q4 plan. |
| `#project-acme` | Priya is taking over Acme after the handoff. |
| `#general` | @soham owns Acme now — confirmed in Linear. |

Use entity names aligned with gold: **Morgan**, **Priya**, **Ethan**, **Acme**, **CedarBank**.

## 4. Live verification matrix

| Step | Human action | Expected |
|------|--------------|----------|
| B6 | `@continuum who owns Acme?` | Current owner + provenance blocks |
| B7 | history / why questions | Evidence-derived answers |
| B8 | `@priya` variant | EntityStore resolution, not Slack hardcode |
| **B9** | Post ownership change in `#project-acme` | Worker ingests without manual reload |
| B9 cont. | `@continuum who owns Acme now?` | Updated owner |
| B10 | `@continuum who owned Acme before Priya?` | Morgan in history |
| B11 | Contradictory messages → resolution | REVIEW then definitive |
| B12 | Thread with clarifying reply | Thread context in artifact |
| B15 | Replay duplicate event | No duplicate claims |
| B16 | Restart worker + bot | Same answer |
| B20 | Reset graph → re-ingest from Slack only | Same semantic state |

## 4b. Live pipeline checklist (for recording)

In Socket Mode the bot posts a **live trace checklist** before the answer, so Slack
shows the reconstruction on camera:

```
Continuum · reconstructing the answer
✓  Searching Slack
✓  Searching Gmail
✓  Resolving entities
✓  Checking timeline
✓  Collecting evidence
```

then the answer:

```
Priya owns Acme now.
Previously: Morgan
Effective: Aug 5
Evidence: Slack · Gmail
Confidence: High
```

Each ✓ reflects a stage that actually ran (a source that returned evidence, entity
resolution, timeline, evidence collection) — nothing is faked; a stage with no
signal shows a hollow `◦`.

Controls (env):

| Var | Default (socket) | Effect |
|-----|------------------|--------|
| `CONTINUUM_SLACK_TRACE` | `1` (on) | Post the checklist before the answer |
| `CONTINUUM_SLACK_TRACE_DELAY` | `0.8` | Seconds between checklist and answer (pace for camera) |

**Dry-run preview** (no Slack app needed — renders exactly what will post, from the
live canonical state; requires HydraDB seeded per steps 1–3 or the golden path):

```bash
python scripts/run_slack_bot.py --mode once --text "who owns Acme?"
python scripts/run_slack_bot.py --mode once --text "who owned Acme before Priya?"
```

Seed the golden-path state first if not using live Slack ingest:

```bash
python scripts/demo_console.py reset
python scripts/demo_console.py seed              # Slack: Morgan owns Acme
python scripts/demo_console.py apply gmail-transition
python scripts/demo_console.py apply gmail-aug5  # → Priya, effective Aug 5
```

## 5. Automated harness (no live Slack)

```bash
python3 -m pytest tests/pipeline/test_memory_worker.py tests/delivery/test_slack_demo_harness.py -m hydradb -q
```

## 6. Final gate

```bash
make source-e2e               # must stay 20/20
python3 -m pytest tests -q
python3 -m pytest -m hydradb -q
make test-sources test-delivery
```
