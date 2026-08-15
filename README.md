# Continuum

Continuum is being built on HydraDB.

## Current phase

Phase 2B — Real claims / evidence harness (contract v1 locked, Gate 2 checkpoint verdict recorded)

Status:

- Shared Artifact/Mention/Claim contract v1, single-sourced in `continuum/claims/`
- Extraction pipeline (deterministic + hybrid): `continuum/extract/`, `continuum/eval/`
- Claim ingestion boundary into HydraDB (`continuum/hydradb/claims.py`)
- Generalized state/provenance/conflict/abstention queries (`continuum/query/state.py`)
- Claim-handoff verifier (`make checkpoint-claims`): per-claim failure codes
  for every candidate claim (611 currently: 455 MISSING_TIMESTAMP,
  156 INVALID_SUBJECT, 0 graph-loadable)
- Known-good real-claim fixture (10 hand-validated claims on real dsid
  artifacts) with regression tests: current/historical state, provenance,
  conflict, abstention, non-OWNS predicates, reset
- Canonical state-result envelope across all queries (`continuum/query/result.py`)
- One-command workflows: `make checkpoint-claims`, `make real-claims-e2e`,
  `make eval-real-claims`
- Phase 3 groundwork: entity-resolution design doc, 87 labeled identity
  pairs, HydraDB query-shape measurements, benchmark strategy + 20-question
  eval set
- 80+ tests green (unit + HydraDB integration; Phase 0 + 1 + 2A regression)

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

