"""Cross-source gold fixture (Section 8) — the central regression scenario.

Slack announces a handoff; Gmail confirms the transfer with an explicit
effective date. The two sources must fuse into ONE company state:

    entity          : Acme
    previous owner  : Morgan
    current owner   : Priya
    transition      : effective 2026-08-01
    evidence        : Slack + Gmail

This exercises the SAME core the product uses (resolve → extract → gate →
load → answer). No source-specific reasoning anywhere.
"""

from __future__ import annotations

import pytest

from continuum.benchmark import answer
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import (
    artifact_source_fixture,
    artifact_to_claim_fixture,
    load_claims,
    wipe_for_entities,
)
from continuum.pipeline.source_e2e import (
    claim_dict_to_model,
    extract_claim_records,
    gate_claims_for_load,
    resolve_entities_from_artifacts,
)
from continuum.sources.gmail.models import GmailMessage, GmailParticipant
from continuum.sources.gmail.normalize import normalize_gmail_message
from continuum.sources.slack.models import SlackMessage
from continuum.sources.slack.normalize import normalize_slack_message


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


def _slack(ts: str, author_id: str, author_name: str, text: str, ingested_at: str) -> object:
    return normalize_slack_message(
        SlackMessage(
            ts=ts,
            channel_id="C07ACME",
            channel_name="account-updates",
            text=text,
            user_id=author_id,
            user_display=author_name,
            workspace_id="T0ACME01",
            workspace_subdomain="redwood-acme",
        ),
        ingested_at=ingested_at,
    )


def _gmail(msg_id: str, sender: str, body: str, date: str, ingested_at: str) -> object:
    return normalize_gmail_message(
        GmailMessage(
            message_id=msg_id,
            thread_id="gmail-acme-thread",
            subject="Acme ownership",
            body=body,
            from_participant=GmailParticipant(name=sender, email=f"{sender.lower()}@company.com"),
            to_participants=[GmailParticipant(name="ops", email="ops@company.com")],
            timestamp=date,
        ),
        ingested_at=ingested_at,
    )


def _load(client: HydraDBClient, artifacts) -> dict:
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
    EntityStore(client).save(entities, reset=False)
    return resolutions


@pytest.fixture(scope="module")
def gold_state(client: HydraDBClient) -> dict:
    slack = _slack(
        "1785196800.000000", "U01PRI", "Priya", "Priya is taking over Acme.",
        ingested_at="2026-07-28T00:00:00+00:00",
    )
    gmail = _gmail(
        "gmail-gold-1", "Morgan",
        "Effective August 1, ownership of Acme transfers from Morgan to Priya.",
        "Fri, 01 Aug 2026 09:00:00 +0000",
        ingested_at="2026-08-01T00:00:00+00:00",
    )
    resolutions = _load(client, [slack, gmail])
    return {"resolutions": resolutions}


@pytest.mark.hydradb
def test_gold_entities_converge(gold_state: dict):
    keys = set(gold_state["resolutions"].keys())
    assert "account:acme" in keys
    assert "person:priya" in keys
    assert "person:morgan" in keys


@pytest.mark.hydradb
def test_gold_current_owner_is_priya_effective_aug1(client: HydraDBClient, gold_state: dict):
    now = answer(
        client,
        {"question_id": "gold_now", "question": "Who owns Acme now?", "predicate": "OWNS", "evidence_entity": "account:acme"},
    )
    state = now["state_result"]
    assert state["status"] == "definitive"
    assert state["value"]["name"] == "Priya"
    assert state["valid_from"] == "2026-08-01"  # the transition effective date


@pytest.mark.hydradb
def test_gold_previous_owner_is_morgan(client: HydraDBClient, gold_state: dict):
    before = answer(
        client,
        {"question_id": "gold_before", "question": "Who owned Acme before Priya?", "predicate": "OWNS", "evidence_entity": "account:acme"},
    )
    assert before["state_result"]["value"]["name"] == "Morgan"


@pytest.mark.hydradb
def test_gold_evidence_spans_both_sources(client: HydraDBClient, gold_state: dict):
    now = answer(
        client,
        {"question_id": "gold_ev_now", "question": "Who owns Acme now?", "predicate": "OWNS", "evidence_entity": "account:acme"},
    )
    before = answer(
        client,
        {"question_id": "gold_ev_before", "question": "Who owned Acme before Priya?", "predicate": "OWNS", "evidence_entity": "account:acme"},
    )
    sources = {e.get("source") for e in now["evidence"]} | {e.get("source") for e in before["evidence"]}
    assert {"Slack", "Gmail"} <= sources


@pytest.mark.hydradb
def test_gold_query_trace_is_safe_and_complete(client: HydraDBClient, gold_state: dict):
    from continuum.query.trace import build_query_trace, render_trace

    question = {
        "question_id": "gold_trace", "question": "Who owns Acme now?",
        "predicate": "OWNS", "evidence_entity": "account:acme",
    }
    trace = build_query_trace(client, question)

    # Complete: every stage present (Sec 20).
    assert trace["decomposition"]["intent"]
    assert trace["state"]["owner"] == "Priya"
    assert trace["temporal"]["valid_from"] == "2026-08-01"
    assert {"Slack", "Gmail"} <= set(trace["evidence"]["sources"])
    assert trace["evidence"]["multi_source"] is True

    # Safe: no raw private content, no tokens anywhere in the rendered trace.
    rendered = render_trace(trace)
    assert "transfers from Morgan" not in rendered  # no raw message body
    assert "token" not in rendered.lower()
    assert "Priya" in rendered


@pytest.mark.hydradb
def test_gold_ranked_evidence_is_cross_source(client: HydraDBClient, gold_state: dict):
    from continuum.query.semantic import StateQueryAdapter

    adapter = StateQueryAdapter(client)
    ranked = adapter.get_ranked_evidence("account:acme", "OWNS")
    summary = ranked["cross_source"]
    # One fact, corroborated by both source systems (Sec 10).
    assert summary["multi_source"] is True
    assert {"Slack", "Gmail"} <= set(summary["sources"])
    # The strongest evidence leads and supports the current owner.
    assert summary["top"] is not None
    assert "Priya" in str(summary["top"].get("subject_mention"))


@pytest.mark.hydradb
def test_gold_graph_reflects_cross_source(client: HydraDBClient, gold_state: dict):
    # Section 17: the exported graph shows Morgan -> Acme -> Priya with evidence
    # nodes from BOTH sources — one graph, not source-specific graphs.
    from continuum.query.graph_export import export_graph

    graph = export_graph(client, "account:acme")
    names = {n.get("name") for n in graph["nodes"] if n.get("type") == "entity"}
    assert {"Morgan", "Priya"} <= names

    owns_edges = [(e["source"], e["target"]) for e in graph["edges"] if e["rel"] == "OWNS"]
    assert ("person:morgan", "account:acme") in owns_edges
    assert ("person:priya", "account:acme") in owns_edges

    source_names = {n.get("name") for n in graph["nodes"] if n.get("type") == "source"}
    assert {"Slack", "Gmail"} <= source_names


@pytest.mark.hydradb
def test_gold_mcp_matches_slack_state(client: HydraDBClient, gold_state: dict):
    # Section 18: MCP returns the SAME state the Slack bot consumes — both are
    # thin transports over the one query layer.
    from continuum.delivery.mcp_adapter import ContinuumMCPAdapter

    mcp = ContinuumMCPAdapter(client)
    mcp_state = mcp.call("get_current_state", {"entity_key": "account:acme", "predicate": "OWNS"})

    # The Slack bot answers via the same core (answer -> state_result).
    slack_answer = answer(
        client,
        {"question_id": "gold_slack", "question": "Who owns Acme now?", "predicate": "OWNS", "evidence_entity": "account:acme"},
    )
    slack_state = slack_answer["state_result"]

    assert mcp_state["status"] == slack_state["status"] == "definitive"
    assert mcp_state["value"]["name"] == slack_state["value"]["name"] == "Priya"
    assert mcp_state["valid_from"] == slack_state["valid_from"] == "2026-08-01"

    # MCP also exposes as-of and history over the same state.
    hist = mcp.call("get_history", {"entity_key": "account:acme"})
    assert hist["status"] == "definitive"


@pytest.mark.hydradb
def test_gold_slack_block_kit_shows_cross_source(client: HydraDBClient, gold_state: dict):
    from continuum.delivery.slack_formatter import format_slack_answer

    slack_answer = answer(
        client,
        {"question_id": "gold_fmt", "question": "Who owns Acme now?", "predicate": "OWNS", "evidence_entity": "account:acme"},
    )
    rendered = format_slack_answer(slack_answer)
    text = rendered["text"]
    assert "Priya owns Acme now." in text
    assert "Slack" in text and "Gmail" in text  # both sources cited
    assert isinstance(rendered["blocks"], list) and rendered["blocks"]

