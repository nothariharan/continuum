#!/usr/bin/env python3
"""Canonical cross-source company-memory demo (Sections 15 / 26).

Deterministic, fixtures-based (no live credentials). Proves that Slack + Gmail
fuse into ONE temporal memory, and that NEW Gmail information changes the
answer to the SAME question — without manually rebuilding the graph.

    Slack : Morgan owns Acme.
    Gmail : ownership of Acme transfers from Morgan to Priya effective Aug 1.
    Q     : who owns Acme now?         -> Priya, effective Aug 1 (Slack + Gmail)
    Gmail : correction, effective Aug 3
    Q     : who owns Acme now?         -> Priya, effective Aug 3
    Q     : who owned it before Priya? -> Morgan
    graph : Morgan -> Acme -> Priya    (evidence from Slack + Gmail)
    MCP   : get_current_state(acme)    -> same state

Usage:  python scripts/demo_cross_source.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is importable when run directly (the gate step imports
# scripts.checkpoint_claims, which requires 'scripts' to be a top-level package).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from continuum.benchmark import answer
from continuum.delivery.mcp_adapter import ContinuumMCPAdapter
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
from continuum.query.graph_export import export_graph
from continuum.sources.gmail.models import GmailMessage, GmailParticipant
from continuum.sources.gmail.normalize import normalize_gmail_message
from continuum.sources.slack.models import SlackMessage
from continuum.sources.slack.normalize import normalize_slack_message


def slack(ts, name, text, ingested):
    return normalize_slack_message(
        SlackMessage(ts=ts, channel_id="C_ACME", channel_name="account-updates", text=text,
                     user_id=f"U_{name}", user_display=name, workspace_id="T", workspace_subdomain="redwood"),
        ingested_at=ingested,
    )


def gmail(mid, sender, body, date, ingested):
    return normalize_gmail_message(
        GmailMessage(message_id=mid, thread_id="acme", subject="Acme ownership", body=body,
                     from_participant=GmailParticipant(name=sender, email=f"{sender.lower()}@company.com"),
                     to_participants=[GmailParticipant(name="ops", email="ops@company.com")], timestamp=date),
        ingested_at=ingested,
    )


def ingest(client, artifacts):
    """Run the automated pipeline: resolve -> extract -> gate -> load. No manual graph edits."""
    resolutions, entities = resolve_entities_from_artifacts(artifacts)
    claims, _ = extract_claim_records(artifacts, resolutions, refinement_provider="mock")
    loadable, _ = gate_claims_for_load(claims, resolutions, artifacts)
    wipe_for_entities(client, resolutions.keys())
    fixture_artifacts = [artifact_to_claim_fixture(a) for a in artifacts]
    sources = {}
    for a in artifacts:
        s = artifact_source_fixture(a)
        sources[s["key"]] = s
    load_claims(client, claims=[claim_dict_to_model(r) for r in loadable], resolutions=resolutions,
                fixture_artifacts=fixture_artifacts, fixture_sources=list(sources.values()), reset=True)
    EntityStore(client).save(entities, reset=False)


def ask(client, question):
    res = answer(client, {"question_id": "demo", "question": question, "predicate": "OWNS", "evidence_entity": "account:acme"})
    state = res["state_result"]
    sources = sorted({e.get("source") for e in res["evidence"] if e.get("source")})
    return state, sources


def line(s):
    print(s, flush=True)


def run(client) -> dict:
    # STEP 1-2: seed Slack + Gmail (transfer effective Aug 1)
    a_slack = slack("1785196800.000000", "Morgan", "Morgan owns Acme.", "2026-07-20T00:00:00+00:00")
    a_gmail1 = gmail("g1", "Morgan", "Effective August 1, ownership of Acme transfers from Morgan to Priya.",
                     "Fri, 01 Aug 2026 09:00:00 +0000", "2026-08-01T00:00:00+00:00")
    ingest(client, [a_slack, a_gmail1])

    line("STEP 1  Slack : Morgan owns Acme.")
    line("STEP 2  Gmail : ownership transfers Morgan -> Priya effective Aug 1.")
    state, sources = ask(client, "Who owns Acme now?")
    line(f"STEP 3  Q: who owns Acme now?  -> {state['value']['name']} (effective {state['valid_from']}) via {' + '.join(sources)}")
    first_effective = state["valid_from"]

    # STEP 4: NEW Gmail correction (effective Aug 3) — re-ingested automatically.
    a_gmail2 = gmail("g2", "Morgan", "Correction: ownership of Acme transfers from Morgan to Priya effective August 3.",
                     "Sun, 03 Aug 2026 09:00:00 +0000", "2026-08-03T00:00:00+00:00")
    ingest(client, [a_slack, a_gmail1, a_gmail2])
    line("STEP 4  Gmail : correction — effective Aug 3.")

    state2, sources2 = ask(client, "Who owns Acme now?")
    line(f"STEP 5  Q: who owns Acme now?  -> {state2['value']['name']} (effective {state2['valid_from']}) via {' + '.join(sources2)}")
    second_effective = state2["valid_from"]

    before, _ = ask(client, "Who owned Acme before Priya?")
    line(f"STEP 6  Q: who owned it before Priya?  -> {before['value']['name']}")

    graph = export_graph(client, "account:acme")
    entity_names = sorted({n["name"] for n in graph["nodes"] if n.get("type") == "entity"})
    source_names = sorted({n["name"] for n in graph["nodes"] if n.get("type") == "source"})
    line(f"STEP 7  graph : entities={entity_names}  sources={source_names}")

    mcp = ContinuumMCPAdapter(client)
    mcp_state = mcp.call("get_current_state", {"entity_key": "account:acme", "predicate": "OWNS"})
    line(f"STEP 8  MCP  : get_current_state(acme) -> {mcp_state['value']['name']} (effective {mcp_state['valid_from']})")

    return {
        "first_effective": first_effective,
        "second_effective": second_effective,
        "current_owner": state2["value"]["name"],
        "previous_owner": before["value"]["name"],
        "graph_entities": entity_names,
        "graph_sources": source_names,
        "mcp_owner": mcp_state["value"]["name"],
        "mcp_effective": mcp_state["valid_from"],
    }


def main() -> int:
    try:
        client = HydraDBClient()
        client.__enter__()
        client.health_check()
    except Exception as exc:  # noqa: BLE001
        line(f"HydraDB required for this demo: {exc}")
        return 1
    try:
        result = run(client)
    finally:
        client.__exit__(None, None, None)
    ok = (
        result["first_effective"] == "2026-08-01"
        and result["second_effective"] == "2026-08-03"
        and result["current_owner"] == "Priya"
        and result["previous_owner"] == "Morgan"
        and result["mcp_owner"] == "Priya"
    )
    line("")
    line("ACCEPTANCE: new Gmail info changed the answer (Aug 1 -> Aug 3) with no manual graph rebuild."
         if ok else "ACCEPTANCE FAILED")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
