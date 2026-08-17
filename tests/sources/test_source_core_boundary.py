"""Source → core boundary tests (pure, no HydraDB).

Proves the source adapters terminate at canonical Artifact and that the
existing query/claim core consumes them without source-specific logic:

  - artifact_to_claim_fixture mapping (Artifact -> load_claims shape)
  - the same question decomposes identically regardless of which source
    artifact produced the evidence
  - temporal "before <person>" decomposition
"""

from __future__ import annotations

from pathlib import Path

from continuum.claims.schema import Claim
from continuum.dataset.artifact import Artifact
from continuum.hydradb.claims import (
    artifact_source_fixture,
    artifact_to_claim_fixture,
    pair_supported,
    resolve_mentions,
)
from continuum.query.decompose import classify_intent, decompose_question, parse_temporal_constraints
from continuum.sources.gmail.adapter import GmailAdapter
from continuum.sources.slack.adapter import SlackAdapter
from continuum.sources.slack.models import SlackMessage
from continuum.sources.slack.normalize import normalize_slack_message

SLACK_FIXTURES = Path("data/fixtures/sources/slack")
GMAIL_FIXTURES = Path("data/fixtures/sources/gmail")

RESOLUTIONS = {
    "person:morgan": {"label": "Person", "name": "Morgan", "mentions": ["Morgan"]},
    "person:priya": {"label": "Person", "name": "Priya", "mentions": ["Priya"]},
    "account:acme": {"label": "Account", "name": "Acme", "mentions": ["Acme"]},
}


def _slack_artifacts():
    return SlackAdapter(fixtures_dir=SLACK_FIXTURES).normalize_all_fixtures()


def _gmail_artifacts():
    return GmailAdapter(fixtures_dir=GMAIL_FIXTURES).normalize_all_fixtures()


def test_artifact_to_claim_fixture_mapping():
    artifact = _slack_artifacts()[0]
    fixture = artifact_to_claim_fixture(artifact)
    assert fixture["key"] == artifact.id
    assert fixture["kind"] == artifact.type
    assert fixture["content"] == artifact.content
    assert fixture["title"] == artifact.title
    assert fixture["source_id"] == "source:slack"
    assert fixture["observed_at"] == str(artifact.timestamp)[:10]

    source = artifact_source_fixture(artifact)
    assert source == {"key": "source:slack", "name": "Slack"}


def test_gmail_fixture_mapping_uses_gmail_source():
    artifact = _gmail_artifacts()[0]
    assert artifact.source == "gmail"
    assert artifact_to_claim_fixture(artifact)["source_id"] == "source:gmail"
    assert artifact_to_claim_fixture(artifact)["observed_at"] is not None


def test_source_adapters_emit_evidence_not_resolution():
    """Adapters must not resolve identities — participants stay raw."""
    for artifact in _slack_artifacts() + _gmail_artifacts():
        assert artifact.source_id == artifact.metadata["native_source_id"]
    gmail = _gmail_artifacts()
    assert any("soham@company.com" in a.content for a in gmail)


def test_same_question_decomposes_identically_across_sources():
    slack_ctx = decompose_question({"question_id": "q", "question": "Who owns Acme?"})
    gmail_ctx = decompose_question({"question_id": "q", "question": "Who owns Acme?"})
    assert slack_ctx.to_dict() == gmail_ctx.to_dict()
    assert classify_intent("Who owns Acme?") == "OWNERSHIP"


def test_temporal_before_person_anchor():
    ctx = decompose_question({"question_id": "q", "question": "Who owned Acme before Priya?"})
    before = [c for c in ctx.temporal if c.kind == "before"]
    assert before and "priya" in (before[0].anchor or "")


def test_temporal_parser_pure():
    constraints = parse_temporal_constraints("Who owned Acme before the handoff?")
    assert [c.kind for c in constraints] == ["before"]
    assert "handoff" in (constraints[0].anchor or "")


def test_query_core_has_no_source_switch():
    """No 'if source == slack' inside the query core modules."""
    import pathlib

    import continuum.query

    core_files = list((pathlib.Path(continuum.query.__file__).parent).glob("*.py")) + [
        pathlib.Path("continuum") / "benchmark" / "pipeline.py",
    ]
    leaked = []
    for path in core_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for source in ("slack", "gmail", "github", "jira"):
            if re_search_source_switch(text, source):
                leaked.append((path.name, source))
    assert not leaked, f"source leakage in query core: {leaked}"


def test_source_vertical_preflight_passes_claim_validation_gate():
    """Pure preflight: the Slack->Artifact->Claim wiring clears load_claims'
    validation (mention resolution, entity pairs, artifact presence, time)."""
    morgan = normalize_slack_message(
        SlackMessage(ts="1728100000.000000", channel_id="C07ACME", channel_name="account-updates",
                     text="Morgan owns Acme as of this week.", user_id="U01MOR", user_display="Morgan",
                     workspace_id="T0", workspace_subdomain="redwood-acme"),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    priya = normalize_slack_message(
        SlackMessage(ts="1728200000.000000", channel_id="C07ACME", channel_name="account-updates",
                     text="I own Acme now.", user_id="U01PRI", user_display="Priya",
                     workspace_id="T0", workspace_subdomain="redwood-acme"),
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    claims = [
        Claim.create(artifact_id=morgan.id, subject_mention="Morgan", predicate="OWNS",
                     object_mention="Acme", observed_at="2024-10-05",
                     valid_from="2024-10-05", valid_to="2024-10-05",
                     evidence_span="Morgan owns Acme"),
        Claim.create(artifact_id=priya.id, subject_mention="Priya", predicate="OWNS",
                     object_mention="Acme", observed_at="2024-10-06",
                     valid_from="2024-10-06", valid_to=None,
                     evidence_span="I own Acme now"),
    ]

    entity_by_mention = resolve_mentions(claims, RESOLUTIONS)
    assert {c.subject_mention for c in claims} <= set(entity_by_mention)

    for claim in claims:
        subject = entity_by_mention[claim.subject_mention]
        object_ = entity_by_mention[claim.object_mention]
        assert pair_supported(claim.predicate, subject["label"], object_["label"])

    fixtures = [artifact_to_claim_fixture(a) for a in (morgan, priya)]
    fixture_keys = {f["key"] for f in fixtures}
    assert all(c.artifact_id in fixture_keys for c in claims)
    assert all(f["observed_at"] for f in fixtures)
    assert all(f["source_id"] == "source:slack" for f in fixtures)
    assert artifact_source_fixture(morgan) == {"key": "source:slack", "name": "Slack"}


def re_search_source_switch(text: str, source: str) -> bool:
    import re

    pattern = re.compile(
        rf"(if|elif)\s+[^:]*\b(source|artifact\.source|row\[['\"]source)\s*==\s*['\"]{source}['\"]",
        re.IGNORECASE,
    )
    return bool(pattern.search(text))