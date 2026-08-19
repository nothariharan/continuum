"""Batch 8 — MCP adapter contract tests (canned envelopes, no transport)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from continuum.delivery.mcp_adapter import ContinuumMCPAdapter
from continuum.query.result import result as make_result


def _adapter() -> ContinuumMCPAdapter:
    client = MagicMock()
    adapter = ContinuumMCPAdapter(client, entity_store=MagicMock())
    return adapter


def test_tool_catalog_is_mcp_shaped():
    tools = _adapter().tools()
    names = {t["name"] for t in tools}
    assert names == {"ask", "get_current_state", "get_history", "get_conflicts", "get_evidence", "resolve_entity", "export_graph"}
    for tool in tools:
        assert tool["name"] and tool["description"]
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert isinstance(schema["properties"], dict)
        assert isinstance(schema["required"], list)
        # every required key is declared
        assert all(k in schema["properties"] for k in schema["required"])


def test_get_current_state_returns_canonical_envelope():
    adapter = _adapter()
    adapter._semantic.get_current_state = MagicMock(  # noqa: SLF001
        return_value=make_result("account:acme", "OWNS", "definitive", value={"name": "Priya"}, valid_from="2026-08-01")
    )
    out = adapter.call("get_current_state", {"entity_key": "account:acme"})
    assert out["status"] == "definitive"
    assert out["value"]["name"] == "Priya"
    # contract envelopes are JSON-serializable (MCP requires JSON)
    json.dumps(out)


def test_ask_delegates_to_query_service():
    adapter = _adapter()
    canned = {"question_id": "mcp", "status": "definitive", "state_result": {"status": "definitive"}}
    adapter._query.ask = MagicMock(return_value=canned)  # noqa: SLF001
    out = adapter.call("ask", {"question": "who owns Acme?"})
    assert out == canned
    adapter._query.ask.assert_called_once()  # noqa: SLF001


def test_unknown_tool_raises():
    adapter = _adapter()
    try:
        adapter.call("nonexistent", {})
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_missing_required_argument_raises():
    adapter = _adapter()
    try:
        adapter.call("get_current_state", {})
        raised = False
    except KeyError:
        raised = True
    assert raised
