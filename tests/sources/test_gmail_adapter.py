"""Tests for Gmail adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from continuum.extract.deterministic import DeterministicMentionExtractor
from continuum.sources.gmail.adapter import GmailAdapter
from continuum.sources.validate import validate_artifact_boundary

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "sources" / "gmail"


@pytest.fixture
def adapter() -> GmailAdapter:
    return GmailAdapter(fixtures_dir=FIXTURES)


def test_gmail_fixture_count(adapter: GmailAdapter):
    assert len(adapter.normalize_all_fixtures()) == 3


def test_gmail_artifact_fields(adapter: GmailAdapter):
    for artifact in adapter.normalize_all_fixtures():
        assert artifact.source == "gmail"
        assert artifact.type == "gmail_message"
        assert artifact.source_id == artifact.metadata["message_id"]
        validate_artifact_boundary(artifact, require_metadata=True)


def test_gmail_participants_not_pre_resolved(adapter: GmailAdapter):
    artifact = next(a for a in adapter.normalize_all_fixtures() if "soham@company.com" in a.content)
    emails = {p["email"] for p in artifact.metadata["participants"]}
    assert "soham@company.com" in emails
    assert "sarah.chen@redwood.com" in emails
    assert "finance-ops@redwood.com" in emails


def test_gmail_thread_id_preserved(adapter: GmailAdapter):
    artifacts = adapter.normalize_all_fixtures()
    handoff = next(a for a in artifacts if a.metadata["message_id"] == "gmail-msg-001")
    reply = next(a for a in artifacts if a.metadata["message_id"] == "gmail-msg-002")
    assert handoff.metadata["thread_id"] == reply.metadata["thread_id"]


def test_gmail_source_url(adapter: GmailAdapter):
    artifact = next(a for a in adapter.normalize_all_fixtures() if a.metadata["message_id"] == "gmail-api-msg-003")
    assert artifact.metadata["source_url"].startswith("https://mail.google.com/")


def test_gmail_mention_extractor_smoke(adapter: GmailAdapter):
    extractor = DeterministicMentionExtractor()
    for artifact in adapter.normalize_all_fixtures():
        assert isinstance(extractor.extract(artifact), list)
