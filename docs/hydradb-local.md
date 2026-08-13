# HydraDB local development

Continuum uses the official HydraDB Docker image and keeps HydraDB source as a pinned Git submodule at `hydradb/hydradb-repo`. HydraDB code is not modified by Continuum.

## Start

Install Docker Desktop and Python 3.12+. Copy `.env.example` to `.env` if changing defaults. Run:

```powershell
.\scripts\start_hydradb.ps1
```

The script pulls `ghcr.io/hydra-db/hydradb` pinned to the checked-out HydraDB commit, creates `hydradb-data/`, starts one `graph-node`, and waits for readiness.

Services and ports:

| Surface | Address | Use |
|---|---|---|
| Bolt | `127.0.0.1:7687` | Continuum application queries |
| Query HTTP | `127.0.0.1:8443` | HydraDB-native HTTP API; not used by the Continuum client |
| Admin | `127.0.0.1:9090` | `/readyz` readiness and `/metrics` |

HydraDB is run in local plaintext mode only. The auth token is stored in `hydradb-data/auth-token`, which is ignored by Git.

## Health and connection

```powershell
python -m continuum.hydradb.health
```

Continuum uses the official Python `neo4j` driver over Bolt. The configured database is `default`; the graph namespace and cell are the local HydraDB defaults `default` and `cell-0`.

## Stop and reset

```powershell
.\scripts\stop_hydradb.ps1
.\scripts\reset_hydradb.ps1
```

Reset stops only the `continuum-hydradb` container and deletes only the configured workspace-local `hydradb-data/` directory. It never deletes arbitrary Docker volumes or user databases. Start again to recreate an empty store.

Equivalent Make targets are available where `make` is installed: `make hydradb-up`, `make hydradb-health`, `make hydradb-reset`, and `make hydradb-smoke`.

