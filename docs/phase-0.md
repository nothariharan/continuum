# Phase 0 report

## Runtime

HydraDB is a Rust graph database with a `graph-node` data/query service and an optional asynchronous indexer. Phase 0 runs one official `graph-node` Docker image backed by a local object-store directory. No MinIO, S3, Kubernetes, indexer, or source build is required for this local foundation.

The official local runtime exposes Bolt `7687`, query HTTP `8443`, and admin `9090`. Readiness is checked at `GET /readyz`; metrics are available at `GET /metrics`. A listening port alone is not considered ready.

## Connection

Continuum’s primary protocol is Neo4j-compatible Bolt through the official Python `neo4j` driver. The thin client connects to `bolt://127.0.0.1:7687`, authenticates with the local token, and selects database `default`.

## Query

OpenCypher statements are sent through Bolt. Parameters use `$name` placeholders and are passed as driver parameters, never string concatenation. Each client result includes `elapsed_ms`.

## Write

Creates use `CREATE` and idempotent setup uses `MERGE` followed by `SET` where needed. Batch writes use HydraDB’s documented client-transport form `UNWIND $rows AS row ...`; the list of maps is passed as a single Bolt parameter.

## Traversal

The smoke graph proves directed `Sarah -OWNS-> Acme` traversal inside HydraDB. A bounded variable-length pattern `[:OWNS*1..2]` is also exercised. HydraDB requires an explicit maximum path length; unbounded `*` traversal is intentionally unsupported.

## Reset

`reset_hydradb.ps1` stops the Continuum-owned container and removes only `hydradb-data/`. The next start recreates the local object store, cache, and token file. The smoke flow resets before and after execution and is run twice.

## Problems discovered

- HydraDB’s Docker image requires local plaintext to be explicitly enabled for this development flow.
- HydraDB requires `RUST_MIN_STACK=33554432`; the official image startup script supplies it.
- The official repository warns that readiness is not proof of queryability, so health includes a trivial authenticated Bolt query.
- HydraDB implements a deliberate OpenCypher subset. One statement is accepted per request, node IDs are non-negative integers, and batch list parameters are supported through the client transport.
- Windows has no `make` in the current workspace, so PowerShell scripts are the primary documented commands; the Makefile remains available for compatible environments.

