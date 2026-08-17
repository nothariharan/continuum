"""Tests for incremental sync cursor persistence."""

from __future__ import annotations

import json
from pathlib import Path

from continuum.sources.cursor import SyncCursor
from continuum.sources.slack.adapter import SlackAdapter
from continuum.sources.sync import load_cursor, save_cursor


def test_save_and_load_cursor(tmp_path: Path):
    cursor = SyncCursor(source="slack", value="C07:1.2", last_sync_at="2026-08-17T10:00:00+00:00")
    path = tmp_path / "slack.cursor.json"
    save_cursor(cursor, path)
    loaded = load_cursor(path)
    assert loaded == cursor


def test_incremental_fetch_updates_cursor_file(tmp_path: Path):
    fixtures = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "sources" / "slack"
    adapter = SlackAdapter(fixtures_dir=fixtures)
    cursor_path = tmp_path / "slack.cursor.json"

    page1 = adapter.fetch(limit=2)
    save_cursor(page1.next_cursor or adapter.cursor(page1.records[-1]), cursor_path)

    cursor = load_cursor(cursor_path)
    page2 = adapter.fetch(cursor=cursor, limit=2)
    assert len(page2.records) == 2

    out_path = tmp_path / "cursor.json"
    save_cursor(adapter.cursor(page2.records[-1]), out_path)
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["source"] == "slack"
    assert "value" in data
