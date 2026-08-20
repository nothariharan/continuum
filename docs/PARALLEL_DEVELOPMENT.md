# Parallel Development Tracks

Two branches run in parallel without cross-contamination:

| Track | Branch | Owner focus |
|-------|--------|-------------|
| Benchmark ER | `feature/benchmark-er-v1` | Measurable Continuum improvement on dev 80Q |
| Product / demo | `feature/product-ui` | Landing, live demo, graph viz, MCP inspector |

## Product UI (`feature/product-ui`)

Demo surfaces (all build clean with `npm run build` in `web/`):

| Route | Purpose |
|-------|---------|
| `/` | Premium landing + feature grid |
| `/query` | Live query console |
| `/graph` | Knowledge graph explorer |
| `/slack` | Slack demo interface |
| `/mcp` | MCP inspector / agent tools |
| `/demo` | Autoplay demo player |
| `/connectors` | Source connector matrix |
| `/trust` | Provenance & temporal trust |

**Do not** change benchmark Makefile targets, subset manifests, or eval scoring on this branch.

## Benchmark ER (`feature/benchmark-er-v1`)

- Failure clusters: `docs/benchmark-er-v1-failure-clusters.md`
- Resolver-only changes in `continuum/entities/*`
- Graph dev run: `make benchmark-subset-er-dev` (HydraDB port 7688)

**Do not** merge `experiment/benchmark-20pct` — experiment-only diagnosis branch.
