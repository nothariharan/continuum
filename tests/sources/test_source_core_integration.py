"""Source -> Continuum core vertical integration tests (hydradb).

Proves the full path for Slack AND Gmail through the SAME core:

    source fixture -> Artifact -> claims -> entity resolution -> HydraDB
      -> QueryContext -> temporal/conflict -> answer -> source provenance

Requires a running local HydraDB (hydradb marker).
"""

from __future__ import annotations

import pytest

from continuum.benchmark import answer
from continuum.claims.schema import Claim
from continuum.hydradb import HydraDBClient
from continuum.hydradb.artifacts import delete_all_artifacts
from continuum.hydradb.claims import (
    artifact_source_fixture,
    artifact_to_claim_fixture,
    load_claims,
)
from continuum.query.decompose import decompose_question
from continuum.query.failures import classify_result
from continuum.sources.gmail.models import GmailMessage, GmailParticipant
from continuum.sources.gmail.normalize import normalize_gmail_message
from continuum.sources.slack.models import SlackMessage
from continuum.sources.slack.normalize import normalize_slack_message


@pytest.fixture(scope="module", autouse=True)
def clean_artifact_graph():
    """Clear pre-existing Artifact nodes so anchor/evidence resolution only
    sees the fixtures this module loads (deterministic vertical tests)."""
    try:
        with HydraDBClient() as client:
            client.health_check()
            delete_all_artifacts(client)
    except Exception as exc:
        pytest.skip(f"HydraDB must be running for source integration tests: {exc}")

CHANNEL = "C07ACME"
WORKSPACE = "T0ACME01"
SUB = "redwood-acme"


def _slack(msg_ts: str, author_id: str, author_name: str, text: str) -> SlackMessage:
    return SlackMessage(
        ts=msg_ts,
        channel_id=CHANNEL,
        channel_name="account-updates",
        text=text,
        user_id=author_id,
        user_display=author_name,
        workspace_id=WORKSPACE,
        workspace_subdomain=SUB,
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


def _load(client, artifacts, claims, resolutions):
    fixture_artifacts = [artifact_to_claim_fixture(a) for a in artifacts]
    sources = {}
    for a in artifacts:
        s = artifact_source_fixture(a)
        sources[s["key"]] = s
    return load_claims(
        client,
        claims=claims,
        resolutions=resolutions,
        fixture_artifacts=fixture_artifacts,
        fixture_sources=list(sources.values()),
        reset=True,
    )


RESOLUTIONS = {
    "person:morgan": {"label": "Person", "name": "Morgan", "mentions": ["Morgan"]},
    "person:priya": {"label": "Person", "name": "Priya", "mentions": ["Priya"]},
    "person:soham": {
        "label": "Person",
        "name": "Soham",
        "mentions": ["Soham", "@soham", "soham@company.com"],
    },
    "account:acme": {"label": "Account", "name": "Acme", "mentions": ["Acme"]},
}


@pytest.mark.hydradb
def test_slack_temporal_handoff_vertical(client: HydraDBClient):
    morgan = _slack("1728100000.000000", "U01MOR", "Morgan", "Morgan owns Acme as of this week.")
    priya = _slack("1728200000.000000", "U01PRI", "Priya", "Taking over Acme ownership today. I own Acme now.")
    morgan_a = normalize_slack_message(morgan, ingested_at="2026-01-01T00:00:00+00:00")
    priya_a = normalize_slack_message(priya, ingested_at="2026-01-01T00:00:00+00:00")

    claims = [
        Claim.create(
            artifact_id=priya_a.id, subject_mention="Priya", predicate="OWNS",
            object_mention="Acme", observed_at="2024-10-06",
            valid_from="2024-10-06", valid_to=None,
            evidence_span="I own Acme now",
        ),
        Claim.create(
            artifact_id=morgan_a.id, subject_mention="Morgan", predicate="OWNS",
            object_mention="Acme", observed_at="2024-10-05",
            valid_from="2024-10-05", valid_to="2024-10-05",
            evidence_span="Morgan owns Acme as of this week",
        ),
    ]
    _load(client, [morgan_a, priya_a], claims, RESOLUTIONS)

    now = answer(client, {
        "question_id": "q_slack_now",
        "question": "Who owns Acme now?",
        "predicate": "OWNS",
        "evidence_entity": "account:acme",
    })
    assert now["query_context"]["intent"] == "OWNERSHIP"
    assert now["state_result"]["status"] == "definitive"
    assert now["state_result"]["value"]["name"] == "Priya"
    assert classify_result(now) == "OK"

    before = answer(client, {
        "question_id": "q_slack_before",
        "question": "Who owned Acme before Priya?",
        "predicate": "OWNS",
        "evidence_entity": "account:acme",
    })
    assert before["state_result"]["status"] == "definitive"
    assert before["state_result"]["value"]["name"] == "Morgan"
    assert before["state_result"]["resolution"] == "before"

    evidence_sources = {e.get("source") for e in before["evidence"]}
    assert "Slack" in evidence_sources


@pytest.mark.hydradb
def test_gmail_vertical(client: HydraDBClient):
    msg = _gmail(
        "gmail-msg-77", "gmail-thread-77", "soham",
        "Soham owns Acme now. Handoff complete.",
        "Mon, 07 Oct 2024 09:00:00 +0000",
    )
    artifact = normalize_gmail_message(msg, ingested_at="2026-01-01T00:00:00+00:00")
    assert artifact.source == "gmail"
    assert artifact.metadata["message_id"] == "gmail-msg-77"
    assert "soham@company.com" in artifact.content

    claim = Claim.create(
        artifact_id=artifact.id, subject_mention="Soham", predicate="OWNS",
        object_mention="Acme", observed_at="2024-10-07",
        valid_from="2024-10-07", valid_to=None,
        evidence_span="Soham owns Acme now",
    )
    _load(client, [artifact], [claim], RESOLUTIONS)

    result = answer(client, {
        "question_id": "q_gmail",
        "question": "Who owns Acme now?",
        "predicate": "OWNS",
        "evidence_entity": "account:acme",
    })
    assert result["state_result"]["value"]["name"] == "Soham"
    sources = {e.get("source") for e in result["evidence"]}
    assert "Gmail" in sources


@pytest.mark.hydradb
def test_conflicting_slack_evidence(client: HydraDBClient):
    morgan = normalize_slack_message(
        _slack("1728100000.000000", "U01MOR", "Morgan", "Morgan owns Acme."),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    priya = normalize_slack_message(
        _slack("1728100000.100000", "U01PRI", "Priya", "Priya owns Acme too."),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    claims = [
        Claim.create(
            artifact_id=morgan.id, subject_mention="Morgan", predicate="OWNS",
            object_mention="Acme", observed_at="2024-10-05",
            valid_from="2024-10-05", valid_to=None,
            evidence_span="Morgan owns Acme",
        ),
        Claim.create(
            artifact_id=priya.id, subject_mention="Priya", predicate="OWNS",
            object_mention="Acme", observed_at="2024-10-05",
            valid_from="2024-10-05", valid_to=None,
            evidence_span="Priya owns Acme too",
        ),
    ]
    _load(client, [morgan, priya], claims, RESOLUTIONS)

    result = answer(client, {
        "question_id": "q_conflict",
        "question": "Who actually owns Acme right now?",
        "predicate": "OWNS",
        "evidence_entity": "account:acme",
    })
    assert result["state_result"]["status"] in {"conflict", "review"}
    assert classify_result(result) == "CONFLICT_MISS"
    assert result["conflicts"]


@pytest.mark.hydradb
def test_cross_source_ownership(client: HydraDBClient):
    gmail_morgan = normalize_gmail_message(
        _gmail("gmail-msg-1", "gmail-thread-1", "morgan", "Morgan owns Acme.", "Tue, 01 Oct 2024 09:00:00 +0000"),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    slack_priya = normalize_slack_message(
        _slack("1728345600.000000", "U01PRI", "Priya", "Priya is taking over Acme."),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    claims = [
        Claim.create(
            artifact_id=gmail_morgan.id, subject_mention="Morgan", predicate="OWNS",
            object_mention="Acme", observed_at="2024-10-01",
            valid_from="2024-10-01", valid_to="2024-10-07",
            evidence_span="Morgan owns Acme",
        ),
        Claim.create(
            artifact_id=slack_priya.id, subject_mention="Priya", predicate="OWNS",
            object_mention="Acme", observed_at="2024-10-08",
            valid_from="2024-10-08", valid_to=None,
            evidence_span="Priya is taking over Acme",
        ),
    ]
    _load(client, [gmail_morgan, slack_priya], claims, RESOLUTIONS)

    now = answer(client, {
        "question_id": "q_xs_now",
        "question": "Who owns Acme now?",
        "predicate": "OWNS",
        "evidence_entity": "account:acme",
    })
    assert now["state_result"]["value"]["name"] == "Priya"

    before = answer(client, {
        "question_id": "q_xs_before",
        "question": "Who owned Acme before Priya?",
        "predicate": "OWNS",
        "evidence_entity": "account:acme",
    })
    assert before["state_result"]["value"]["name"] == "Morgan"

    now_sources = {e.get("source") for e in now["evidence"]}
    before_sources = {e.get("source") for e in before["evidence"]}
    assert "Slack" in now_sources
    assert "Gmail" in before_sources


@pytest.mark.hydradb
def test_entity_resolution_across_sources(client: HydraDBClient):
    slack = normalize_slack_message(
        _slack("1728345600.000000", "U01SOH", "Soham", "@soham owns Acme now."),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    gmail = normalize_gmail_message(
        _gmail("gmail-msg-9", "gmail-thread-9", "soham", "soham@company.com owns Acme.", "Wed, 09 Oct 2024 09:00:00 +0000"),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    claims = [
        Claim.create(
            artifact_id=slack.id, subject_mention="Soham", predicate="OWNS",
            object_mention="Acme", observed_at="2024-10-08",
            valid_from="2024-10-08", valid_to=None,
            evidence_span="@soham owns Acme now",
        ),
        Claim.create(
            artifact_id=gmail.id, subject_mention="Soham", predicate="OWNS",
            object_mention="Acme", observed_at="2024-10-09",
            valid_from="2024-10-09", valid_to=None,
            evidence_span="soham@company.com owns Acme",
        ),
    ]
    _load(client, [slack, gmail], claims, RESOLUTIONS)

    result = answer(client, {
        "question_id": "q_entity",
        "question": "Who owns Acme now?",
        "predicate": "OWNS",
        "evidence_entity": "account:acme",
    })
    assert result["state_result"]["value"]["name"] == "Soham"
    sources = {e.get("source") for e in result["evidence"]}
    assert {"Slack", "Gmail"} <= sources