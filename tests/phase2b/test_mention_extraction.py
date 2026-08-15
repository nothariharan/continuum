"""Deterministic mention extraction tests."""

from continuum.dataset.artifact import Artifact
from continuum.extract.deterministic import DeterministicMentionExtractor


def _artifact(source: str, content: str, **kwargs) -> Artifact:
    return Artifact(
        id=kwargs.get("id", "dsid_test123456789012345678901234567890"),
        source=source,
        source_id="test123456789012345678901234567890",
        type=f"{source}_message",
        author=kwargs.get("author"),
        timestamp=kwargs.get("timestamp"),
        title=kwargs.get("title"),
        content=content,
        metadata=kwargs.get("metadata") or {},
    )


def test_gmail_header_mentions():
    artifact = _artifact(
        "gmail",
        "Subject: Test\n\nFrom: Sarah Chen <sarah@example.com>\nTo: Arjun Mehta <arjun@example.com>",
    )
    mentions = DeterministicMentionExtractor().extract(artifact)
    texts = {(m.raw_text, m.type) for m in mentions}
    assert ("Sarah Chen", "person") in texts
    assert ("sarah@example.com", "email") in texts


def test_slack_person_and_username():
    artifact = _artifact(
        "slack",
        "Noah: Poll question\nZoe: Captain Crunch\n@soham-dev: agreed",
    )
    mentions = DeterministicMentionExtractor().extract(artifact)
    texts = {m.raw_text for m in mentions}
    assert "Noah" in texts
    assert "Zoe" in texts
    assert "@soham-dev" in texts


def test_ticket_mentions_across_sources():
    artifact = _artifact("jira", "Fix ENG-5842 blocking SUP-19344 rollout")
    mentions = DeterministicMentionExtractor().extract(artifact)
    tickets = {m.raw_text for m in mentions if m.type == "ticket"}
    assert "ENG-5842" in tickets
    assert "SUP-19344" in tickets
