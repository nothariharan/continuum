# Continuum Product UI

Next.js marketing + product surface for Continuum company memory.

## Develop

```bash
# Terminal 1 — backend
make hydradb-up
make run-query-api

# Terminal 2 — web
make web-dev
```

Set `NEXT_PUBLIC_CONTINUUM_API=http://127.0.0.1:8080` in `web/.env.local` for live query/graph export.

Without the API, the site uses deterministic demo fixtures.

## Routes

- `/` — full marketing story
- `/demo?autoplay=1` — deterministic Acme ownership demo
- `/graph?entity=account:acme` — graph explorer

## Stack

- Next.js 15 App Router
- Tailwind CSS v4
- Framer Motion
- @xyflow/react
