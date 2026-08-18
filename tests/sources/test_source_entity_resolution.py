"""B3 regression tests — signal-driven entity resolution (PR #10 review).

Locks:
- no hardcoded alias whitelist and no deletion of unseen entities
- cross-source identity converges from artifact signals (Slack username ==
  Gmail local-part), deterministically
- entity-resolution questions use the SAME canonical identity as extraction
- ambiguous identities can abstain instead of guessing
"""

from __future__ import annotations

from continuum.dataset.artifact import Artifact
from continuum.pipeline.source_e2e import (
    _person_entity_key,
    resolve_entities_from_artifacts,
)

GMAIL = "gmail"
SLACK = "slack"


def _artifact(
    source: str,
    author: str,
    content: str,
    *,
    participants: list[dict] | None = None,
    timestamp: str = "2026-07-01T00:00:00+00:00",
) -> Artifact:
    return Artifact(
        id=f"dsid_{abs(hash((source, author, content))) % 10**32:032x}",
        source=source,
        source_id=f"{source}-1",
        type="gmail_message" if source == GMAIL else "slack_message",
        author=author,
        timestamp=timestamp,
        title="t",
        content=content,
        metadata={"participants": participants or []},
    )


def _entity_keys(artifacts: list[Artifact]) -> dict[str, dict]:
    resolutions, _ = resolve_entities_from_artifacts(artifacts)
    return resolutions


def test_person_entity_key_signal_precedence():
    assert _person_entity_key("Soham Ratnaparkhi", email="", username="@soham") == "person:soham"
    assert _person_entity_key("Soham", email="soham@company.com", username="") == "person:soham"
    assert _person_entity_key("Soham Ratnaparkhi") == "person:soham-ratnaparkhi"


def test_cross_source_email_and_handle_converge():
    slack = _artifact(
        SLACK, "Soham Ratnaparkhi", "Soham Ratnaparkhi: @soham owns Acme now.",
        participants=[{"user_id": "U1", "display_name": "Soham Ratnaparkhi", "username": "soham"}],
    )
    gmail = _artifact(
        GMAIL, "soham <soham@company.com>", "soham@company.com owns Acme.",
        participants=[{"email": "soham@company.com", "display_name": "soham <soham@company.com>"}],
    )
    resolutions = _entity_keys([slack, gmail])
    soham = resolutions.get("person:soham") or {}
    mentions = {m.lower() for m in soham.get("mentions", [])}
    assert "@soham" in mentions
    assert "soham@company.com" in mentions
    assert "soham ratnaparkhi" in mentions
    assert "person:soham-ratnaparkhi" not in resolutions


def test_gmail_local_part_and_slack_username_converge():
    slack = _artifact(
        SLACK, "Maya Patel", "Maya Patel: I still own CedarBank.",
        participants=[{"user_id": "U2", "display_name": "Maya Patel", "username": "maya.patel"}],
    )
    gmail = _artifact(
        GMAIL, "Maya Patel <maya.patel@redwood.com>", "maya.patel@redwood.com handed off CedarBank.",
        participants=[{"email": "maya.patel@redwood.com", "display_name": "Maya Patel <maya.patel@redwood.com>"}],
    )
    resolutions = _entity_keys([slack, gmail])
    assert "person:maya-patel" in resolutions
    maya = resolutions["person:maya-patel"]
    mentions = {m.lower() for m in maya["mentions"]}
    assert "maya patel" in mentions
    assert "maya.patel@redwood.com" in mentions


def test_distinct_names_do_not_falsely_merge():
    a = _artifact(SLACK, "Sarah Chen", "Sarah Chen: owns Acme.",
                  participants=[{"user_id": "U3", "display_name": "Sarah Chen", "username": "sarah.chen"}])
    b = _artifact(SLACK, "Sara King", "Sara King: owns Acme.",
                  participants=[{"user_id": "U4", "display_name": "Sara King", "username": "sara.king"}])
    resolutions = _entity_keys([a, b])
    assert "person:sarah-chen" in resolutions
    assert "person:sara-king" in resolutions
    assert len(resolutions) >= 2


def test_unseen_entities_are_not_deleted():
    # The old implementation deleted every entity not in a hardcoded
    # keep-list. A brand-new person must survive resolution.
    artifact = _artifact(
        GMAIL, "Priya Nair <priya.nair@company.com>", "Priya Nair owns NovaCorp.",
        participants=[{"email": "priya.nair@company.com", "display_name": "Priya Nair <priya.nair@company.com>"}],
    )
    resolutions = _entity_keys([artifact])
    assert "person:priya-nair" in resolutions


def test_account_entities_from_handoff_text():
    artifact = _artifact(GMAIL, "Maya Patel <maya.patel@redwood.com>", "handing off CedarBank account ownership",
                         participants=[{"email": "maya.patel@redwood.com", "display_name": "Maya Patel"}])
    resolutions = _entity_keys([artifact])
    assert "account:cedarbank" in resolutions


def test_ambiguous_identity_absent_instead_of_forced_merge():
    # Two mentions with no shared signal must NOT be forced together.
    a = _artifact(GMAIL, "John Smith <john.smith@corp-a.com>", "John Smith owns Acme.",
                  participants=[{"email": "john.smith@corp-a.com", "display_name": "John Smith"}])
    b = _artifact(GMAIL, "john <john@corp-b.com>", "john owns Acme.",
                  participants=[{"email": "john@corp-b.com", "display_name": "john"}])
    resolutions = _entity_keys([a, b])
    assert "person:john-smith" in resolutions
    assert "person:john" in resolutions
