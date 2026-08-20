# Continuum — Deployment (demo)

Make the already-working golden path reachable outside a laptop. The frontend
goes to **Vercel**; the backend runs as a **self-contained Continuum runtime**
(HydraDB + Query API) via Docker. Same canonical memory behind Web, Slack, MCP.

```
                 INTERNET
        ┌───────────┴───────────┐
        ▼                       ▼
  Continuum web             Slack Events
   (Vercel)                     │
        │                       ▼
        └──────────►  CONTINUUM API (Docker)  ◄── MCP (uv run continuum-mcp)
                             │
                          HydraDB
```

## 1. Backend runtime (HydraDB + Query API)

On any Docker host (your machine, a VM, a small cloud box):

```bash
cd deploy
# optional: set the frontend origin so CORS allows it
export CONTINUUM_ALLOWED_ORIGINS="https://<your-vercel-domain>"
docker compose up -d --build
```

This starts:
- `hydradb` on `:7687` (bolt) / `:9090` (readyz)
- `continuum-api` on `:8080` (FastAPI)

Seed the golden path into the deployed graph (from the repo root, pointing at the
running HydraDB):

```bash
make demo-reset && make demo-seed
make demo-apply EVENT=gmail-transition
make demo-apply EVENT=gmail-aug5
```

Health check the API:

```bash
curl http://<host>:8080/health          # {"status":"ok"}
curl http://<host>:8080/v1/connectors   # real connector state
```

Expose `:8080` publicly (reverse proxy / tunnel / cloud host). For HTTPS, put it
behind a proxy (Caddy/Nginx/Cloudflare Tunnel).

## 2. Frontend (Vercel)

The web app reads the API base from `NEXT_PUBLIC_CONTINUUM_API`.

```bash
cd web
vercel                     # first deploy (preview)
# set env for the project:
vercel env add NEXT_PUBLIC_CONTINUUM_API   # -> https://<your-api-host>
vercel --prod              # production
```

If `NEXT_PUBLIC_CONTINUUM_API` is unset or unreachable, the UI runs in **DEMO
mode** (clearly labelled) — it never fabricates "connected" state.

## 3. MCP (Option A — local/private)

No hosting needed for the hackathon:

```json
{ "mcpServers": { "continuum": { "command": "uv", "args": ["run", "continuum-mcp"] } } }
```

See `docs/mcp-setup.md`.

## 4. Verify the golden path end-to-end (deployed)

Ask "Who owns Acme now?" and confirm the **same** answer across:
- Web  → `/query`
- Slack → `@continuum who owns Acme?`
- MCP  → `get_current_state(account:acme)`
- Graph → `/graph`

All four resolve from the one canonical memory.

## Notes
- Single-company model — one workspace, one HydraDB. Multi-tenant onboarding is
  intentionally out of scope for the demo.
- `.env` at repo root (or `HYDRADB_*` env) configures the DB connection; defaults
  match the local dev token.
