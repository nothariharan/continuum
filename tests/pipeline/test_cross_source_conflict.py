"""Cross-source conflict + dedup (Sections 12, 14).

Conflict (Sec 12): contradictory ownership across sources with no temporal
winner must resolve to status=conflict/review — never silently pick the
last-ingested source. A later authoritative transfer, with real temporal
evidence, resolves to definitive.

Dedup (Sec 14): the SAME business fact in Slack AND Gmail yields TWO source
artifacts but ONE logical state — provenance is preserved, artifacts are not
collapsed into one document.
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
from continuum.query.conflict import resolve_conflict_state
from continuum.query.state import resolve_provenance, resolve_state
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


def _slack(ts: str, name: str, text: str, ingested_at: str):
    return normalize_slack_message(
        SlackMessage(
            ts=ts, channel_id="C1", channel_name="acct", text=text,
            user_id=f"U_{name}", user_display=name,
            workspace_id="T1", workspace_subdomain="ws",
        ),
        ingested_at=ingested_at,
    )


def _gmail(msg_id: str, sender: str, body: str, date: str, ingested_at: str):
    return normalize_gmail_message(
        GmailMessage(
            message_id=msg_id, thread_id="t", subject="Acme ownership", body=body,
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


# -- Section 12: conflict with no clear winner ------------------------------


@pytest.mark.hydradb
def test_contradiction_same_day_is_conflict_not_guess(client: HydraDBClient):
    # Same observed (business) date, contradictory owners, overlapping open
    # intervals -> the evidence cannot pick a winner. Gmail's date is derived
    # from Slack's normalized observed date so the two always coincide
    # regardless of the test machine's timezone.
    slack = _slack("1788307200.000000", "Priya", "Priya owns Acme.", "2026-09-01T00:00:00+00:00")
    same_day = slack.timestamp[:10]
    gmail = _gmail("g-conf-1", "Morgan", "Morgan owns Acme.", f"{same_day}T09:00:00+00:00", "2026-09-01T00:00:00+00:00")
    assert slack.timestamp[:10] == gmail.timestamp[:10]  # guard the premise
    _load(client, [slack, gmail])

    state = resolve_conflict_state(client, "account:acme", "OWNS")
    assert state["status"] in {"conflict", "review"}
    assert set(state["conflicting_subjects"]) == {"person:priya", "person:morgan"}


@pytest.mark.hydradb
def test_authoritative_transfer_resolves_to_definitive(client: HydraDBClient):
    # A later authoritative transfer with an explicit effective date establishes
    # disjoint intervals -> succession is definitive (Morgan -> Priya).
    gmail = _gmail(
        "g-conf-2", "Morgan",
        "Effective September 5, ownership of Acme transfers from Morgan to Priya.",
        "Fri, 05 Sep 2026 09:00:00 +0000", "2026-09-05T00:00:00+00:00",
    )
    _load(client, [gmail])

    state = resolve_conflict_state(client, "account:acme", "OWNS")
    assert state["status"] == "definitive"
    assert state["value"]["name"] == "Priya"
    assert state["resolution"] == "succession-disjoint-intervals"


@pytest.mark.hydradb
def test_later_business_time_supersedes_not_ingest_order(client: HydraDBClient):
    # Gmail (Morgan) has an EARLIER business time; Slack (Priya) a LATER one.
    # Even though Gmail is passed second (ingested last), the resolver picks the
    # later business observation, not the ingest order.
    gmail = _gmail("g-conf-3", "Morgan", "Morgan owns Acme.", "Wed, 01 Jan 2026 09:00:00 +0000", "2026-01-01T00:00:00+00:00")
    slack = _slack("1780704000.000000", "Priya", "Priya owns Acme.", "2026-06-06T00:00:00+00:00")
    # Note ingest order: gmail passed AFTER slack.
    _load(client, [slack, gmail])

    state = resolve_conflict_state(client, "account:acme", "OWNS")
    assert state["status"] == "definitive"
    assert state["value"]["name"] == "Priya"
    assert state["resolution"] == "superseded-by-later-observation"


# -- Section 14: same fact, two sources, one logical state ------------------


@pytest.mark.hydradb
def test_same_fact_two_sources_one_state_two_artifacts(client: HydraDBClient):
    slack = _slack("1788307200.000000", "Priya", "Priya owns Acme.", "2026-09-01T00:00:00+00:00")
    gmail = _gmail("g-dup-1", "Priya", "Priya owns Acme.", "Tue, 01 Sep 2026 09:00:00 +0000", "2026-09-01T00:00:00+00:00")
    artifacts = [slack, gmail]
    # Two distinct source artifacts (not collapsed).
    assert len({a.id for a in artifacts}) == 2
    assert {a.source for a in artifacts} == {"slack", "gmail"}

    _load(client, artifacts)

    # One logical state: a single current owner.
    state = resolve_state(client, "account:acme", "OWNS")
    assert state["status"] == "definitive"
    assert state["value"]["name"] == "Priya"

    # Provenance retains BOTH source artifacts as evidence.
    prov = resolve_provenance(client, "account:acme", "OWNS")
    sources = {e.get("source") for e in prov["evidence"]}
    assert {"Slack", "Gmail"} <= sources
    artifact_ids = {e.get("artifact_id") for e in prov["evidence"]}
    assert len(artifact_ids) >= 2
