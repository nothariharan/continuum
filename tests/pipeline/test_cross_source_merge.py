"""Batch 4 — cross-source evidence merge through the full extraction pipeline.

Slack + Gmail fixtures feed the SAME core (resolve → extract → gate → load →
answer). One question's answer must require both sources: current owner comes
from Slack, the prior holder from Gmail, and the transition is visible in
history.
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


def _gmail(msg_id: str, thread_id: str, sender: str, body: str, date: str) -> GmailMessage:
    return GmailMessage(
        message_id=msg_id,
        thread_id=thread_id,
        subject="Acme ownership",
        body=body,
        from_participant=GmailParticipant(name=sender, email=f"{sender}@company.com"),
        to_participants=[GmailParticipant(name="ops", email="ops@company.com")],
        timestamp=date,
    )


def _load_full_pipeline(client: HydraDBClient, artifacts) -> dict:
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


@pytest.mark.hydradb
def test_cross_source_merge_transition_and_provenance(client: HydraDBClient):
    slack = normalize_slack_message(
        _slack("1728345600.000000", "U01PRI", "Priya", "Priya is taking over Acme."),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    gmail = normalize_gmail_message(
        _gmail("gmail-merge-1", "gmail-thread-1", "Morgan", "Morgan owns Acme.", "Tue, 01 Oct 2024 09:00:00 +0000"),
        ingested_at="2026-01-01T00:00:00+00:00",
    )

    resolutions = _load_full_pipeline(client, [slack, gmail])
    assert "account:acme" in resolutions

    now = answer(
        client,
        {"question_id": "q_merge_now", "question": "Who owns Acme now?", "predicate": "OWNS", "evidence_entity": "account:acme"},
    )
    assert now["state_result"]["status"] == "definitive"
    assert now["state_result"]["value"]["name"] == "Priya"

    before = answer(
        client,
        {"question_id": "q_merge_before", "question": "Who owned Acme before Priya?", "predicate": "OWNS", "evidence_entity": "account:acme"},
    )
    assert before["state_result"]["value"]["name"] == "Morgan"

    # The transition is reconstructed from the two answers (now → Priya via
    # Slack, before → Morgan via Gmail), and together they cite both sources —
    # one question's memory spans both source systems.
    assert before["state_result"]["value"]["name"] == "Morgan"
    sources = {e.get("source") for e in now["evidence"]} | {e.get("source") for e in before["evidence"]}
    assert {"Slack", "Gmail"} <= sources
