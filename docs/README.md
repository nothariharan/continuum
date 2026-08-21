# Documentation

Documentation for [Continuum](../README.md), organized by topic. Start with the
[project README](../README.md) for an overview and quickstart.

## Setup & operations

| Doc | What it covers |
|-----|----------------|
| [hydradb-local.md](hydradb-local.md) | Local HydraDB lifecycle (start, stop, reset) |
| [mcp-setup.md](mcp-setup.md) | Install and configure the `continuum-mcp` server |
| [slack-demo-script.md](slack-demo-script.md) | Slack bot setup + the live demo runbook |
| [gmail-live-setup.md](gmail-live-setup.md) | Gmail connector credentials and live sync |

## Architecture & contracts

| Doc | What it covers |
|-----|----------------|
| [contract-v1.md](contract-v1.md) | The shared Artifact / Mention / Claim contract |
| [source-ingestion-contract.md](source-ingestion-contract.md) | Source adapter → normalization contract |
| [hydradb-query-shapes.md](hydradb-query-shapes.md) | Measured HydraDB query-shape behavior |
| [query-gap-analysis.md](query-gap-analysis.md) | Query-layer coverage and gaps |

## Benchmark & evaluation

| Doc | What it covers |
|-----|----------------|
| [benchmark-protocol-v1.md](benchmark-protocol-v1.md) | Runnable benchmark protocol (authoritative) |
| [benchmark-scoring.md](benchmark-scoring.md) | Scoring methodology |
| [benchmark-v1-runbook.md](benchmark-v1-runbook.md) | Step-by-step benchmark run |
| [gold-benchmark-v1.md](gold-benchmark-v1.md) | Gold question set |
| [identity-pairs-v1.md](identity-pairs-v1.md) | Labeled identity-resolution pairs |
| [benchmark-strategy.md](benchmark-strategy.md) | Strategy narrative (superseded by the protocol) |

Checkpoint results live in `benchmark-v1-*.md` and `batch-j-benchmark-handoff.md`.

## Development history

The pipeline was built in phase-gated increments. These records document the
design and validation of each stage:

- Pipeline phases — `phase-0.md`, `phase-1.md`, `phase-2-dataset.md`,
  `phase-2b-claims.md`, `phase-2b-extraction.md`, `phase2b-v2-predicate-refinement.md`
- Hackathon execution — `hackathon-execution-plan.md`, `hackathon-execution-progress.md`
- Entity resolution — `phase-3-entity-resolution-design.md`,
  `phase3-entity-resolution-core.md`, `phase3-identity-pairs-scaffold.md`,
  `phase3b-entity-integration.md`, `phase3b-real-identity-validation.md`
- Source → answer — `phase-source-to-answer-e2e.md`,
  `phase-source-to-answer-e2e-report.md`, `phase-source-integration-review.md`
- Slack memory — `slack-company-memory-demo-report.md`,
  `slack-ingestion-checkpoint.md`
- Baselines — `post-stabilization-baseline.md`, `review-pr10-baseline.md`
- Pull-request reviews — [`integration/`](integration/)

## Design research

Background research, strategy blueprints, and architecture plans that informed the system, under
[`research/`](research/):

- Master plans (HTML) — [continuum-master-plan.html](research/continuum-master-plan.html), [continuum_one_year_master_plan.html](research/continuum_one_year_master_plan.html), [continuum_updated_one_year_architecture_plan.html](research/continuum_updated_one_year_architecture_plan.html)
- Hackathon & track blueprints (PDF) — [Hack Hydra Participant Guide.pdf](research/Hack%20Hydra%20Participant%20Guide.pdf), [HydraShield_Technical_Build_Blueprint.pdf](research/HydraShield_Technical_Build_Blueprint.pdf), [HydraShield_Track02A_Problem_and_Solution.pdf](research/HydraShield_Track02A_Problem_and_Solution.pdf)
- Research reports — [hydradb-vision-and-architecture.md](research/hydradb-vision-and-architecture.md), [company-truth-graph-blueprint.md](research/company-truth-graph-blueprint.md), [master-research-report-enterprise-truth-graph.md](research/master-research-report-enterprise-truth-graph.md)
- Series reports — [continuum-01-master-research-report.md](research/continuum-01-master-research-report.md) … [continuum-08](research/continuum-08-hackathon-strategy-red-team-and-hydradb-fit.md)
- Ecosystem & landscape — [curated-ecosystem-and-baselines.md](research/curated-ecosystem-and-baselines.md), [continuum-06-open-source-ecosystem-and-database-comparison.md](research/continuum-06-open-source-ecosystem-and-database-comparison.md)

> These are historical research artifacts written during design and a hackathon
> build; they capture reasoning and prior art, not the current API surface.
