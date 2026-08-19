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
