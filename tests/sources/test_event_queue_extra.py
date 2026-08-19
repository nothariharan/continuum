"""Additional event queue tests — dedup keys, ordering, persistence, malformed input."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from continuum.sources.events import EventQueue, SourceEvent


def _event(event_id: str, native_id: str | None, *, source: str = "slack") -> SourceEvent:
    return SourceEvent(
        event_id=event_id,
        source=source,
        event_type="message",
        native_id=native_id,
        payload={"ok": True},
        received_at="2026-08-18T00:00:00+00:00",
    )


def test_enqueue_different_events(tmp_path: Path):
    queue = EventQueue(tmp_path / "events.jsonl")
    assert queue.enqueue(_event("evt-1", "C1:1.0")) is True
    assert queue.enqueue(_event("evt-2", "C1:2.0")) is True
    assert len(queue.load()) == 2


def test_dedup_same_native_record_different_event_id(tmp_path: Path):
    queue = EventQueue(tmp_path / "events.jsonl")
    assert queue.enqueue(_event("evt-1", "C1:1.0")) is True
    assert queue.enqueue(_event("evt-99", "C1:1.0")) is False


def test_dedup_same_event_id_different_native(tmp_path: Path):
    queue = EventQueue(tmp_path / "events.jsonl")
    assert queue.enqueue(_event("evt-1", "C1:1.0")) is True
    assert queue.enqueue(_event("evt-1", "C2:9.0")) is False


def test_replayed_event_after_reload(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    queue = EventQueue(path)
    assert queue.enqueue(_event("evt-1", "C1:1.0")) is True
    fresh = EventQueue(path)
    assert fresh.enqueue(_event("evt-1", "C1:1.0")) is False


def test_order_preserved_across_reload(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    queue = EventQueue(path)
    for i in range(5):
        queue.enqueue(_event(f"evt-{i}", f"C1:{i}.0"))
    ids = [e.event_id for e in EventQueue(path).load()]
    assert ids == ["evt-0", "evt-1", "evt-2", "evt-3", "evt-4"]


def test_mark_processed_persists_status(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    queue = EventQueue(path)
    queue.enqueue(_event("evt-1", "C1:1.0"))
    queue.mark_processed("evt-1", status="processed")
    events = EventQueue(path).load()
    assert len(events) == 1
    assert events[0].status == "processed"


def test_malformed_line_skipped_not_raised(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"event_id": "ok", "source": "slack", "event_type": "message", "native_id": "C1:1.0", "payload": {}, "received_at": "2026-08-18T00:00:00+00:00"}\n{not-json\n', encoding="utf-8")
    events = EventQueue(path).load()
    assert len(events) == 1
    assert events[0].event_id == "ok"


def test_mark_processed_is_atomic_no_tmp_leftover(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    queue = EventQueue(path)
    queue.enqueue(_event("evt-1", "C1:1.0"))
    queue.mark_processed("evt-1", status="processed")
    assert not path.with_suffix(".jsonl.tmp").exists()
    assert [e.status for e in EventQueue(path).load()] == ["processed"]
