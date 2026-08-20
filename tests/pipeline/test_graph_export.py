"""Batch 7 — knowledge-graph export (read-only) for the demo scenario."""

from __future__ import annotations

import pytest

from continuum.hydradb import HydraDBClient
from continuum.pipeline.source_e2e import (
    claim_dict_to_model,
    extract_claim_records,
    gate_claims_for_load,
    resolve_entities_from_artifacts,
)
from continuum.hydradb.claims import (
    artifact_source_fixture,
    artifact_to_claim_fixture,
    load_claims,
    wipe_for_entities,
)
from continuum.query.graph_export import export_graph
from continuum.sources.slack.models import SlackMessage
from continuum.sources.slack.normalize import normalize_slack_message


@pytest.fixture(scope="module")
def client():
    try:
        value = HydraDBClient()
        value.__enter__()
        value.health_check()
    except Exception as exc:
        pytest.skip(f"HydraDB required: {exc}")
    yield value
    value.__exit__(None, None, None)


def _slack(ts: str, author_id: str, author_name: str, text: str) -> SlackMessage:
    return SlackMessage(
        ts=ts,
        channel_id="C07ACME",
        channel_name="account-updates",
        text=text,
        user_id=author_id,
        user_display=author_name,
        workspace_id="T0ACME01",
        workspace_subdomain="redwood-acme",
    )


@pytest.mark.hydradb
def test_graph_export_contains_demo_nodes_and_edges(client: HydraDBClient):
    artifacts = [
        normalize_slack_message(_slack("1728100000.000000", "U01MOR", "Morgan", "Morgan owns Acme."), ingested_at="2026-01-01T00:00:00+00:00"),
        normalize_slack_message(_slack("1728345600.000000", "U01PRI", "Priya", "Priya is taking over Acme."), ingested_at="2026-01-01T00:00:00+00:00"),
    ]
    resolutions, entities = resolve_entities_from_artifacts(artifacts)
    claims, _ = extract_claim_records(artifacts, resolutions, refinement_provider="mock")
    loadable, _ = gate_claims_for_load(claims, resolutions, artifacts)

    wipe_for_entities(client, resolutions.keys())
    fixture_artifacts = [artifact_to_claim_fixture(a) for a in artifacts]
    sources: dict = {}
    for a in artifacts:
        s = artifact_source_fixture(a)
        sources[s["key"]] = s
    load_claims(
        client,
        claims=[claim_dict_to_model(row) for row in loadable],
        resolutions=resolutions,
        fixture_artifacts=fixture_artifacts,
        fixture_sources=list(sources.values()),
        reset=True,
    )

    graph = export_graph(client, "account:acme")

    node_ids = {n["id"] for n in graph["nodes"]}
    node_types = {n["id"]: n["type"] for n in graph["nodes"]}
    assert "account:acme" in node_ids
    assert "person:morgan" in node_ids and node_types["person:morgan"] == "entity"
    assert "person:priya" in node_ids

    edge_rels = {(e["source"], e["target"], e["rel"]) for e in graph["edges"]}
    # subject -> account predicate edges
    assert ("person:morgan", "account:acme", "OWNS") in edge_rels
    assert ("person:priya", "account:acme", "OWNS") in edge_rels
    # claim -> account (ABOUT), claim -> artifact (SOURCED_FROM), artifact -> source (FROM)
    claim_ids = {n["id"] for n in graph["nodes"] if n["type"] == "claim"}
    assert any(src in claim_ids and tgt == "account:acme" and rel == "ABOUT" for src, tgt, rel in edge_rels)
    assert any(rel == "SOURCED_FROM" for _s, _t, rel in edge_rels)
    assert any(rel == "FROM" for _s, _t, rel in edge_rels)
    # evidence is preserved on claim nodes
    claim_nodes = [n for n in graph["nodes"] if n["type"] == "claim"]
    assert claim_nodes and all(n.get("evidence") for n in claim_nodes)
