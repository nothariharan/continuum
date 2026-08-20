"""Canonical cross-source demo acceptance (Sections 15 / 22 / 26).

The most important manual acceptance test, automated: change Gmail, ask the
SAME question, and the answer changes — without manually rebuilding the graph.
"""

from __future__ import annotations

import pytest

from continuum.hydradb import HydraDBClient


@pytest.fixture(scope="module")
def client():
    try:
        value = HydraDBClient()
        value.__enter__()
        value.health_check()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"HydraDB required: {exc}")
    yield value
    value.__exit__(None, None, None)


@pytest.mark.hydradb
def test_demo_answer_changes_when_gmail_changes(client: HydraDBClient):
    from scripts.demo_cross_source import run

    result = run(client)

    # New Gmail information changed the effective date for the SAME question.
    assert result["first_effective"] == "2026-08-01"
    assert result["second_effective"] == "2026-08-03"
    # Current + previous owner resolved across sources.
    assert result["current_owner"] == "Priya"
    assert result["previous_owner"] == "Morgan"
    # One graph reflects both people and both sources.
    assert {"Morgan", "Priya"} <= set(result["graph_entities"])
    assert {"Slack", "Gmail"} <= set(result["graph_sources"])
    # MCP converges on the same state the query path produced.
    assert result["mcp_owner"] == "Priya"
    assert result["mcp_effective"] == "2026-08-03"
