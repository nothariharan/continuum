# Slack Company Memory Demo Report

**Status:** Template — fill after live matrix B6–B16 with operator in demo workspace.

## Environment

| Item | Value |
|------|-------|
| Commit | _(git rev-parse HEAD)_ |
| HydraDB | _(ports / health)_ |
| Slack mode | live / fixtures |
| Initial ingest report | [slack-demo-initial-ingest.md](./slack-demo-initial-ingest.md) |

## Architecture validated

```
Slack message → EventQueue → MemoryWorker → extract → ER → HydraDB
@continuum → SlackQueryBot → QueryService → benchmark.answer → state
```

## Matrix results

| Step | Action | Pass | Notes |
|------|--------|------|-------|
| B6 | `@continuum who owns Acme?` | ☐ | |
| B7 | history/temporal/why | ☐ | |
| B8 | `@priya` variant | ☐ | |
| B9 | ownership change + re-ask | ☐ | |
| B10 | before Priya | ☐ | |
| B11 | conflict → resolution | ☐ | |
| B12 | thread context | ☐ | |
| B15 | duplicate replay | ☐ | automated harness |
| B16 | restart worker/bot | ☐ | automated harness |
| B20 | reset → re-ingest | ☐ | |

## Automated tests

```bash
python3 -m pytest tests/pipeline/test_memory_worker.py tests/delivery/test_slack_demo_harness.py -m hydradb -q
make source-e2e
```

| Suite | Result |
|-------|--------|
| source-e2e | **20/20** (deterministic × 2) |
| memory_worker | **3/3 passed** |
| demo_harness | **3/3 passed** |
| query core unit | **40/40 passed** |

## Live matrix (operator)

Automated harness covers B9/B15/B16. Steps B6–B12 and B20 require posting in the
demo Slack workspace per [slack-demo-script.md](./slack-demo-script.md).

## Observations

_(Latency, claim counts, failures, operator notes.)_

## STOP boundary

No MCP, 500Q benchmark, Gmail live wiring, or Web UI started after this demo.
