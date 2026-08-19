"""Batch 2 — memory worker reliability (bounded retry, poison events, no wedge).

These exercise the queue/status logic and need no HydraDB: a poison event
fails before ingest, and a pre-seen artifact short-circuits ingest.
"""

from __future__ import annotations

from pathlib import Path

from continuum.dataset.artifact import Artifact
from continuum.pipeline.memory_worker import MemoryWorker
from continuum.sources.events import EventQueue, SourceEvent
from continuum.sources.provenance import utc_now_iso


class _FakeLifecycle:
    source = "slack"

    def __init__(self, records: dict[str, Artifact] | None = None) -> None:
        self._records = records or {}

    def fetch_record(self, native_id: str) -> Artifact | None:
        return self._records.get(native_id)


def _worker(tmp_path: Path, records: dict[str, Artifact] | None = None, *, max_attempts: int = 3) -> MemoryWorker:
    return MemoryWorker(
        client=None,  # type: ignore[arg-type] — unused on poison/skip paths
        queue=EventQueue(tmp_path / "events.jsonl"),
        lifecycle=_FakeLifecycle(records),  # type: ignore[arg-type]
        artifacts_path=tmp_path / "artifacts.jsonl",
        resolutions_path=tmp_path / "resolutions.json",
        max_attempts=max_attempts,
    )


def _event(event_id: str, native_id: str | None) -> SourceEvent:
    return SourceEvent(
        event_id=event_id,
        source="slack",
        event_type="message",
        native_id=native_id,
        payload={},
        received_at=utc_now_iso(),
    )


def test_poison_missing_native_id_bounded_retry_then_failed(tmp_path: Path):
    worker = _worker(tmp_path)
    worker.queue.enqueue(_event("p1", None))
    statuses = [worker.process_pending()[0].status for _ in range(3)]
    assert statuses == ["retry", "retry", "failed"]
    assert [e.status for e in worker.queue.load()] == ["failed"]
    # queue is drained — nothing left pending
    assert worker.process_pending() == []


def test_poison_record_not_found_bounded_retry(tmp_path: Path):
    worker = _worker(tmp_path)
    worker.queue.enqueue(_event("p2", "C1:missing"))
    statuses = [worker.process_pending()[0].status for _ in range(3)]
    assert statuses == ["retry", "retry", "failed"]


def test_poison_does_not_wedge_other_events(tmp_path: Path):
    # A poison event is retried bounded times while a good event (pre-seen
    # artifact) still processes — the queue never wedges.
    artifact = Artifact(
        id="dsid_00000000000000000000000000000001",
        source="slack",
        source_id="C1:1.0",
        type="slack_message",
        author="soham",
        timestamp="2026-08-01T00:00:00+00:00",
        title="t",
        content="hi",
        metadata={"participants": []},
    )
    worker = _worker(tmp_path, records={"C1:1.0": artifact})
    worker._seen_artifacts.add(artifact.id)  # noqa: SLF001 — simulate prior ingest
    worker.queue.enqueue(_event("poison", "C1:missing"))
    worker.queue.enqueue(_event("good", "C1:1.0"))

    first = worker.process_pending()
    assert {r.event_id: r.status for r in first} == {"poison": "retry", "good": "skipped"}

    events = {e.event_id: e.status for e in worker.queue.load()}
    assert events["good"] == "processed"  # skipped is NOT failed
    assert events["poison"] == "pending"  # bounded retry still in flight


def test_skipped_event_marked_processed_not_failed(tmp_path: Path):
    artifact = Artifact(
        id="dsid_00000000000000000000000000000002",
        source="slack",
        source_id="C1:2.0",
        type="slack_message",
        author="soham",
        timestamp="2026-08-01T00:00:00+00:00",
        title="t",
        content="hi",
        metadata={"participants": []},
    )
    worker = _worker(tmp_path, records={"C1:2.0": artifact})
    worker._seen_artifacts.add(artifact.id)  # noqa: SLF001
    worker.queue.enqueue(_event("evt", "C1:2.0"))
    result = worker.process_pending()[0]
    assert result.status == "skipped"
    assert [e.status for e in worker.queue.load()] == ["processed"]
