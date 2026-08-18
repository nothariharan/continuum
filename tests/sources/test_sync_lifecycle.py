"""Tests for SyncLifecycle."""

from __future__ import annotations

from pathlib import Path

from continuum.sources.gmail.adapter import GmailAdapter
from continuum.sources.lifecycle import ConnectorSyncLifecycle
from continuum.sources.slack.adapter import SlackAdapter

FIXTURES_SLACK = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "sources" / "slack"
FIXTURES_GMAIL = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "sources" / "gmail"


def test_initial_sync_idempotent_ids(tmp_path: Path):
    adapter = SlackAdapter(fixtures_dir=FIXTURES_SLACK)
    life = ConnectorSyncLifecycle(adapter, cursor_path=tmp_path / "slack.cursor.json")
    first = life.initial_sync(limit=10)
    second = life.initial_sync(limit=10)
    assert [a.id for a in first.artifacts] == [a.id for a in second.artifacts]


def test_incremental_sync_no_duplicates(tmp_path: Path):
    adapter = SlackAdapter(fixtures_dir=FIXTURES_SLACK)
    life = ConnectorSyncLifecycle(adapter, cursor_path=tmp_path / "slack.cursor.json")
    life.initial_sync(limit=100)
    inc = life.incremental_sync(limit=10)
    assert inc.artifacts == []


def test_source_health_ok():
    adapter = GmailAdapter(fixtures_dir=FIXTURES_GMAIL)
    life = ConnectorSyncLifecycle(adapter)
    health = life.source_health()
    assert health.ok is True
    assert health.source == "gmail"
