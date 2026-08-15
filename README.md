# Continuum

Continuum is being built on HydraDB.

## Current phase

Phase 2B — Real claims / evidence harness

Status:

- Shared Artifact/Mention/Claim contract defined (`continuum/claims/`)
- Claim ingestion boundary into HydraDB (`continuum/hydradb/claims.py`)
- Generalized state/provenance/conflict/abstention queries (`continuum/query/state.py`)
- Real-shaped claim fixture (9 claims, 2-source conflict, abstention target)
- 27/27 integration tests green (Phase 0 + 1 + 2A regression)

Not yet implemented:

- Extraction automation (teammate side, Gate 2 sync)
- Entity resolution (Phase 3)
- RAG
- MCP
- Web UI

See [docs/phase-2b-claims.md](docs/phase-2b-claims.md) for the harness,
[AGENTS.md](AGENTS.md) for the operating contract, and
[docs/hydradb-local.md](docs/hydradb-local.md) for the local lifecycle.

