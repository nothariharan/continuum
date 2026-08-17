"""Tests for Slack adapter and normalization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from continuum.extract.deterministic import DeterministicMentionExtractor
from continuum.sources.slack.adapter import SlackAdapter
from continuum.sources.validate import validate_artifact_boundary

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "sources" / "slack"


@pytest.fixture
def adapter() -> SlackAdapter:
    return SlackAdapter(fixtures_dir=FIXTURES)


def test_each_fixture_normalizes_to_one_artifact(adapter: SlackAdapter):
    artifacts = adapter.normalize_all_fixtures()
    assert len(artifacts) == 5


def test_slack_artifact_fields(adapter: SlackAdapter):
    artifacts = adapter.normalize_all_fixtures()
    for artifact in artifacts:
        assert artifact.source == "slack"
        assert artifact.type == "slack_message"
        assert ":" in artifact.source_id
        assert not artifact.source_id.startswith("dsid_")
        validate_artifact_boundary(artifact, require_metadata=True)


def test_thread_preserves_thread_id_and_participants(adapter: SlackAdapter):
    thread_artifact = next(
        a for a in adapter.normalize_all_fixtures() if a.metadata.get("reply_count", 0) > 0
    )
    assert thread_artifact.metadata["thread_id"] == "1728290000.100000"
    names = {p["display_name"] for p in thread_artifact.metadata["participants"]}
    assert names == {"Jonas Weber", "Sarah Chen"}
    assert "Sarah Chen" in thread_artifact.content


def test_mentions_and_links_metadata(adapter: SlackAdapter):
    artifact = next(
        a for a in adapter.normalize_all_fixtures() if "ENG-9001" in a.content
    )
    assert artifact.metadata.get("source_url", "").startswith("https://")
    assert artifact.metadata["mentions"]
    assert "https://linear.app/redwood/issue/ENG-9001" in artifact.metadata["links"]


def test_idempotent_reingestion(adapter: SlackAdapter):
    first = adapter.normalize_all_fixtures()
    second = adapter.normalize_all_fixtures()
    assert [a.id for a in first] == [a.id for a in second]


def test_deterministic_mention_extractor_smoke(adapter: SlackAdapter):
    extractor = DeterministicMentionExtractor()
    for artifact in adapter.normalize_all_fixtures():
        mentions = extractor.extract(artifact)
        assert isinstance(mentions, list)


def test_fetch_with_cursor_pagination(adapter: SlackAdapter):
    page1 = adapter.fetch(limit=2)
    assert len(page1.records) == 2
    assert page1.next_cursor is not None
    page2 = adapter.fetch(cursor=page1.next_cursor, limit=2)
    assert len(page2.records) == 2
    ids1 = {adapter.normalize(r).id for r in page1.records}
    ids2 = {adapter.normalize(r).id for r in page2.records}
    assert ids1.isdisjoint(ids2)


def test_fixture_files_parse():
    for path in sorted(FIXTURES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "channel_id" in data
        assert "messages" in data
