#!/usr/bin/env python3
"""Golden-path demo library — deterministic Slack+Gmail -> one temporal memory.

This is the reusable engine behind `scripts/demo_console.py`. It drives the SAME
canonical pipeline used in production (resolve -> extract -> gate -> load), reads
its scenario from `demo/golden-path/scenario.json`, and never edits the graph by
hand. Importable and side-effect free.

Design notes:
- Events are ordered in the scenario. Applying an event ingests the cumulative
  prefix of events up to and including it (the loader wipes the demo entities and
  reloads, so passing the full active set keeps state deterministic and idempotent).
- Every read (ask / state / history / graph / mcp) goes through the canonical
  layer, so Web == Slack == Graph == MCP by construction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Make the repo root importable when run directly.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from continuum.benchmark import answer
from continuum.delivery.mcp_adapter import ContinuumMCPAdapter
from continuum.entities.store import EntityStore
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

SCENARIO_PATH = ROOT / "demo" / "golden-path" / "scenario.json"


# ── Scenario ────────────────────────────────────────────────────────────────

def load_scenario(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or SCENARIO_PATH).read_text(encoding="utf-8"))


def event_keys(scenario: dict[str, Any]) -> list[str]:
    return [e["key"] for e in scenario["events"]]


def find_event(scenario: dict[str, Any], key: str) -> dict[str, Any]:
    for e in scenario["events"]:
        if e["key"] == key:
            return e
    raise KeyError(f"unknown event '{key}'. Known: {', '.join(event_keys(scenario))}")


def artifacts_through(scenario: dict[str, Any], key: str) -> list[Any]:
    """Build normalized artifacts for every event up to and including `key`."""
    keys = event_keys(scenario)
    if key not in keys:
        raise KeyError(f"unknown event '{key}'. Known: {', '.join(keys)}")
    upto = keys[: keys.index(key) + 1]
    return [build_artifact(find_event(scenario, k)) for k in upto]


def build_artifact(event: dict[str, Any]) -> Any:
    if event["source"] == "slack":
        author = event["author"]
        return normalize_slack_message(
            SlackMessage(
                ts=event["ts"],
                channel_id="C_ACME",
                channel_name=event.get("channel", "account-updates"),
                text=event["text"],
                user_id=f"U_{author}",
                user_display=author,
                workspace_id="T",
                workspace_subdomain="redwood",
            ),
            ingested_at=event["ingested_at"],
        )
    if event["source"] == "gmail":
        sender = event["sender"]
        return normalize_gmail_message(
            GmailMessage(
                message_id=event["message_id"],
                thread_id=event.get("thread_id", "acme"),
                subject=event.get("subject", "Acme ownership"),
                body=event["body"],
                from_participant=GmailParticipant(name=sender, email=f"{sender.lower()}@company.com"),
                to_participants=[GmailParticipant(name="ops", email="ops@company.com")],
                timestamp=event["date"],
            ),
            ingested_at=event["ingested_at"],
        )
    raise ValueError(f"unknown source '{event['source']}' for event '{event['key']}'")


# ── Pipeline ops (all through the canonical machinery) ───────────────────────

def ingest_artifacts(client, artifacts: list[Any]) -> None:
    """resolve -> extract -> gate -> load. No manual graph edits."""
    resolutions, entities = resolve_entities_from_artifacts(artifacts)
    claims, _ = extract_claim_records(artifacts, resolutions, refinement_provider="mock")
    loadable, _ = gate_claims_for_load(claims, resolutions, artifacts)
    wipe_for_entities(client, resolutions.keys())
    fixture_artifacts = [artifact_to_claim_fixture(a) for a in artifacts]
    sources = {}
    for a in artifacts:
        s = artifact_source_fixture(a)
        sources[s["key"]] = s
    load_claims(
        client,
        claims=[claim_dict_to_model(r) for r in loadable],
        resolutions=resolutions,
        fixture_artifacts=fixture_artifacts,
        fixture_sources=list(sources.values()),
        reset=True,
    )
    EntityStore(client).save(entities, reset=False)


def reset(client, scenario: dict[str, Any]) -> None:
    """Scoped clear of just this demo's entities/artifacts/claims."""
    wipe_for_entities(client, scenario["entity_keys"])


def seed(client, scenario: dict[str, Any]) -> None:
    """Seed the initial Slack state only (the first event)."""
    ingest_artifacts(client, artifacts_through(scenario, event_keys(scenario)[0]))


def apply(client, scenario: dict[str, Any], key: str) -> None:
    """Ingest the cumulative prefix of events up to and including `key`."""
    ingest_artifacts(client, artifacts_through(scenario, key))


def ask(client, scenario: dict[str, Any], question: str) -> dict[str, Any]:
    res = answer(
        client,
        {
            "question_id": "demo",
            "question": question,
            "predicate": scenario["predicate"],
            "evidence_entity": scenario["focus_entity"],
        },
    )
    state = res.get("state_result") or {}
    value = state.get("value") or {}
    sources = sorted({e.get("source") for e in res.get("evidence", []) if e.get("source")})
    return {
        "question": question,
        "status": state.get("status"),
        "owner": value.get("name"),
        "valid_from": state.get("valid_from"),
        "valid_to": state.get("valid_to"),
        "sources": sources,
        "evidence_count": len(res.get("evidence", [])),
        "raw": res,
    }


def slack_answer(client, scenario: dict[str, Any], question: str) -> dict[str, Any]:
    """The exact Slack Block Kit answer the bot would post (same formatter)."""
    from continuum.delivery.slack_formatter import format_slack_answer

    res = answer(
        client,
        {
            "question_id": "demo",
            "question": question,
            "predicate": scenario["predicate"],
            "evidence_entity": scenario["focus_entity"],
        },
    )
    return format_slack_answer(res)


def mcp_state(client, scenario: dict[str, Any]) -> dict[str, Any]:
    mcp = ContinuumMCPAdapter(client)
    return mcp.call(
        "get_current_state",
        {"entity_key": scenario["focus_entity"], "predicate": scenario["predicate"]},
    )


def mcp_history(client, scenario: dict[str, Any]) -> Any:
    mcp = ContinuumMCPAdapter(client)
    return mcp.call(
        "get_history",
        {"entity_key": scenario["focus_entity"], "predicate": scenario["predicate"]},
    )


def graph_summary(client, scenario: dict[str, Any]) -> dict[str, Any]:
    graph = export_graph(client, scenario["focus_entity"])
    return {
        "entities": sorted({n["name"] for n in graph["nodes"] if n.get("type") == "entity"}),
        "sources": sorted({n["name"] for n in graph["nodes"] if n.get("type") == "source"}),
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph.get("edges", [])),
        "raw": graph,
    }
