#!/usr/bin/env python3
"""One-story hackathon demo — incremental company-memory updates.

From a clean graph, replays the demo narrative as a sequence of source
messages and asks Continuum after each turn, printing the resolved answer,
the transition, and the evidence sources. No live Slack needed: each message
is fed as a normalized Slack artifact through the same resolve → extract →
gate → load path the live memory worker uses.

Story:
  1. Morgan owns Acme           -> Morgan
  2. Priya is taking over Acme  -> Priya (the live-update transition)
  3. Morgan still owns Acme     -> still Priya (conflict detection needs
                                   temporal validity windows — Phase 4)
  4. Confirmed: Priya owns Acme -> Priya (definitive)

The headline is step 2: the company's memory changed, and Continuum changed
with it — that is what separates this from "an LLM searching Slack".
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from continuum.benchmark import answer
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
from continuum.sources.slack.models import SlackMessage
from continuum.sources.slack.normalize import normalize_slack_message

STORY = [
    ("Morgan", "Morgan owns Acme per the Q4 plan."),
    ("Priya", "Effective August 1, Priya is taking over Acme from Morgan."),
    ("Morgan", "Morgan still owns Acme."),
    ("Priya", "Confirmed: Priya owns Acme."),
]


def _slack(ts: str, author: str, text: str) -> SlackMessage:
    return SlackMessage(
        ts=ts,
        channel_id="C07ACME",
        channel_name="account-updates",
        text=text,
        user_id=f"U-{author.lower()}",
        user_display=author,
        workspace_id="T0ACME01",
        workspace_subdomain="redwood-acme",
    )


def _ask(client: HydraDBClient, question: str) -> dict:
    return answer(
        client,
        {"question_id": "demo", "question": question, "predicate": "OWNS", "evidence_entity": "account:acme"},
    )


def _ingest_incrementally(client: HydraDBClient, artifacts) -> None:
    resolutions, entities = resolve_entities_from_artifacts(artifacts)
    claims, _ = extract_claim_records(artifacts, resolutions, refinement_provider="mock")
    loadable, _ = gate_claims_for_load(claims, resolutions, artifacts)

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
        reset=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-graph", action="store_true", help="do not wipe the graph first")
    args = parser.parse_args()

    base_ts = 1_728_100_000
    artifacts = []
    with HydraDBClient() as client:
        client.health_check()
        if not args.keep_graph:
            # clean slate for the whole demo scenario
            client.execute("MATCH (c:Claim) DETACH DELETE c")
            client.execute("MATCH (a:Artifact) DETACH DELETE a")
            client.execute("MATCH (s:Source) DETACH DELETE s")

        print("== Continuum company-memory demo ==\n")
        for index, (author, text) in enumerate(STORY):
            artifacts.append(
                normalize_slack_message(_slack(f"{base_ts + index}.000000", author, text), ingested_at="2026-01-01T00:00:00+00:00")
            )
            _ingest_incrementally(client, artifacts)
            print(f"[message {index + 1}] {author}: {text}")
            if index == 0:
                continue  # no question until the transition is in play
            result = _ask(client, "Who owns Acme now?")
            state = result["state_result"]
            status = state["status"]
            value = state.get("value") or {}
            name = value.get("name")
            sources = sorted({e.get("source") for e in result.get("evidence", []) if e.get("source")})
            if status == "definitive":
                print(f"  -> Continuum: {name} owns Acme now.   [evidence: {', '.join(sources)}]")
            elif status in {"conflict", "review"}:
                print(f"  -> Continuum: conflicting evidence — needs review.   [status={status}]")
            else:
                print(f"  -> Continuum: no grounded answer (status={status})")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
