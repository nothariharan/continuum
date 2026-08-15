# Continuum

Continuum is being built on HydraDB.

## Current phase

Phase 2B — Real claims / evidence harness (contract v1 locked, Gate 2 checkpoint verdict recorded)

Status:

- Shared Artifact/Mention/Claim contract v1, single-sourced in `continuum/claims/`
- Extraction pipeline (deterministic + hybrid): `continuum/extract/`, `continuum/eval/`
- Claim ingestion boundary into HydraDB (`continuum/hydradb/claims.py`)
- Generalized state/provenance/conflict/abstention queries (`continuum/query/state.py`)
- 70/70 tests green (unit + HydraDB integration; Phase 0 + 1 + 2A regression)
- Gate 2 checkpoint: 0/50 extracted claims graph-loadable — extraction
  quality (entity-pair claims) is the open blocker before scaling

Not yet implemented:

- Entity-pair claim extraction (teammate fix per Gate 2 verdict)
- Entity resolution (Phase 3)
- RAG
- MCP
- Web UI

See [docs/phase-2b-claims.md](docs/phase-2b-claims.md) for the harness and
checkpoint verdict, [docs/contract-v1.md](docs/contract-v1.md) for the shared
contract, [AGENTS.md](AGENTS.md) for the operating contract, and
[docs/hydradb-local.md](docs/hydradb-local.md) for the local lifecycle.

