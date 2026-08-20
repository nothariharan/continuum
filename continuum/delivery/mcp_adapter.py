"""MCP semantic adapter — a thin tool interface over the existing query layer.

MCP is a transport, not a second implementation. This adapter exposes the
stable semantic operations as MCP-shaped tool definitions plus a ``call``
dispatcher. It re-plumbs NO reasoning — every tool delegates to
``QueryService`` / ``StateQueryAdapter`` / ``export_graph``, which are the
same functions the Slack bot and query API already use.
"""

from __future__ import annotations

from typing import Any

from continuum.delivery.query_service import QueryService
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient
from continuum.query.graph_export import export_graph
from continuum.query.semantic import StateQueryAdapter

_TOOL_SPECS: list[tuple[str, str, dict[str, Any]]] = [
    (
        "ask",
        "Answer a natural-language question about company state with evidence and provenance.",
        {
            "question": {"type": "string", "description": "The question to answer."},
        },
    ),
    (
        "get_current_state",
        "Resolved current state for an entity and predicate.",
        {
            "entity_key": {"type": "string"},
            "predicate": {"type": "string", "default": "OWNS"},
        },
    ),
    (
        "get_state_as_of",
        "Resolved state for an entity and predicate as of a given date (YYYY-MM-DD).",
        {
            "entity_key": {"type": "string"},
            "date": {"type": "string"},
            "predicate": {"type": "string", "default": "OWNS"},
        },
    ),
    (
        "get_history",
        "Ordered history of resolved state transitions for an entity.",
        {
            "entity_key": {"type": "string"},
            "predicate": {"type": "string", "default": "OWNS"},
        },
    ),
    (
        "get_dependencies",
        "Graph dependencies (DEPENDS_ON) for an entity.",
        {"entity_key": {"type": "string"}},
    ),
    (
        "get_conflicts",
        "Conflicting claims about an entity and predicate.",
        {
            "entity_key": {"type": "string"},
            "predicate": {"type": "string", "default": "OWNS"},
        },
    ),
    (
        "get_evidence",
        "Provenance chain (claims -> artifacts -> sources) for an entity.",
        {
            "entity_key": {"type": "string"},
            "predicate": {"type": "string", "default": "OWNS"},
        },
    ),
    (
        "resolve_entity",
        "Map a surface mention to a canonical entity key.",
        {"mention": {"type": "string"}},
    ),
    (
        "export_graph",
        "Export the evidence subgraph for an entity as nodes/edges.",
        {"entity_key": {"type": "string"}},
    ),
]


class ContinuumMCPAdapter:
    """MCP tool surface over the existing Continuum query layer."""

    def __init__(self, client: HydraDBClient, entity_store: EntityStore | None = None) -> None:
        self._client = client
        self._query = QueryService(client, entity_store=entity_store)
        self._semantic = StateQueryAdapter(client, entity_store=entity_store)

    def tools(self) -> list[dict[str, Any]]:
        """MCP-shaped tool definitions (name, description, inputSchema)."""
        out: list[dict[str, Any]] = []
        for name, description, props in _TOOL_SPECS:
            required = [k for k, v in props.items() if "default" not in v]
            out.append(
                {
                    "name": name,
                    "description": description,
                    "inputSchema": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                    },
                }
            )
        return out

    def call(self, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = dict(arguments or {})
        if tool == "ask":
            return self._query.ask(str(arguments.get("question", "")), question_id="mcp")
        if tool == "get_current_state":
            return self._semantic.get_current_state(arguments["entity_key"], arguments.get("predicate", "OWNS"))
        if tool == "get_state_as_of":
            return self._semantic.get_state_as_of(
                arguments["entity_key"], arguments["date"], arguments.get("predicate", "OWNS")
            )
        if tool == "get_dependencies":
            return self._semantic.get_dependencies(arguments["entity_key"])
        if tool == "get_history":
            return self._semantic.get_history(arguments["entity_key"], arguments.get("predicate", "OWNS"))
        if tool == "get_conflicts":
            return self._semantic.get_conflicts(arguments["entity_key"], arguments.get("predicate", "OWNS"))
        if tool == "get_evidence":
            return self._semantic.get_evidence(arguments["entity_key"], arguments.get("predicate", "OWNS"))
        if tool == "resolve_entity":
            return self._semantic.resolve_entity(str(arguments.get("mention", "")))
        if tool == "export_graph":
            return export_graph(self._client, str(arguments.get("entity_key", "")))
        raise ValueError(f"unknown tool: {tool}")
