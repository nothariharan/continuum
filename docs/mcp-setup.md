# Continuum MCP — Setup

Continuum ships a real [Model Context Protocol](https://modelcontextprotocol.io)
server. Any MCP client (Claude Desktop, Cursor, …) can query the **same canonical
company memory** that Slack and the web app use — deterministic, evidence-backed,
never a hallucinated answer.

```
Claude / Agent  →  Continuum MCP  →  Semantic tools  →  Canonical company memory (HydraDB)
```

## Prerequisites

- Python **3.12+**
- [`uv`](https://docs.astral.sh/uv/) installed
- A running HydraDB graph:  `make hydradb-up`  (needs Docker)

## Start the server

```bash
uv run continuum-mcp
# equivalently:  make run-mcp
# or:            python -m continuum.delivery.mcp_server
```

You should see the server come up and expose **9 tools**.

## Register with your client

Add this to your MCP client config (e.g. Claude Desktop
`claude_desktop_config.json`, or Cursor's MCP settings):

```json
{
  "mcpServers": {
    "continuum": {
      "command": "uv",
      "args": ["run", "continuum-mcp"]
    }
  }
}
```

Restart the client. "continuum" appears as a connected MCP server.

## Tools exposed

| Tool | What it does |
|------|--------------|
| `ask` | Natural-language question over canonical state |
| `get_current_state` | Current owner/lead/relationship for an entity |
| `get_history` | Immutable timeline of transitions and prior holders |
| `get_state_as_of` | State at a specific date |
| `get_evidence` | Source artifacts, timestamps, provenance |
| `get_conflicts` | Contradictory claims surfaced for review |
| `resolve_entity` | Fuzzy mention (`@priya`) → canonical id |
| `get_dependencies` | Multi-hop dependencies across teams/services |
| `export_graph` | Read-only entity neighborhood graph |

## Example prompt

> **Who owns the Acme account now, and who had it before?**

Claude calls Continuum over MCP:

```
get_current_state(account:acme)  -> Priya  (since Aug 5)
get_history(account:acme)        -> Morgan -> Priya
```

→ *Priya owns Acme now. Previously Morgan.* Grounded in Slack + Gmail.

## Notes

- The MCP server wraps the exact same `QueryService` / `StateQueryAdapter` used by
  the web API and Slack bot, so **MCP answers == Web == Slack == Graph** by design.
- Official MCP Registry / Smithery publishing is intentionally deferred — this
  local `uv run continuum-mcp` setup is all that's needed to use it.
