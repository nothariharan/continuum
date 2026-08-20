"""Continuum MCP server (stdio).

Exposes the existing ContinuumMCPAdapter tools over the Model Context Protocol so
any MCP client (Claude Desktop, Cursor, etc.) can query the SAME canonical company
memory that Slack and the web app use.

Run it:

    uv run continuum-mcp        # or:  python -m continuum.delivery.mcp_server

MCP client config:

    {
      "mcpServers": {
        "continuum": { "command": "uv", "args": ["run", "continuum-mcp"] }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
from typing import Any


def _run() -> None:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    from continuum.delivery.mcp_adapter import ContinuumMCPAdapter
    from continuum.hydradb import HydraDBClient

    client = HydraDBClient()
    client.__enter__()
    client.health_check()
    adapter = ContinuumMCPAdapter(client)

    server: Server = Server("continuum")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"])
            for t in adapter.tools()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        result = adapter.call(name, arguments or {})
        return [TextContent(type="text", text=json.dumps(result, default=str, indent=2))]

    async def serve() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    try:
        asyncio.run(serve())
    finally:
        client.__exit__(None, None, None)


def main() -> None:
    _run()


if __name__ == "__main__":
    main()
