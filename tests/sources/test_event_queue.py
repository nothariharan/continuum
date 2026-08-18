"""Tests for event queue deduplication."""

from __future__ import annotations

from pathlib import Path

from continuum.sources.events import EventQueue, SourceEvent


def test_enqueue_dedup(tmp_path: Path):
    queue = EventQueue(tmp_path / "events.jsonl")
    event = SourceEvent(
        event_id="evt-1",
        source="slack",
        event_type="message",
        native_id="C1:1.0",
        payload={"ok": True},
        received_at="2026-08-18T00:00:00+00:00",
    )
    assert queue.enqueue(event) is True
    assert queue.enqueue(event) is False
