"""Memory worker tests — fixture events → incremental graph (hydradb)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from continuum.hydradb import HydraDBClient
from continuum.hydradb.artifacts import delete_all_artifacts
from continuum.hydradb.claims import wipe_for_entities
from continuum.pipeline.memory_worker import MemoryWorker
from continuum.sources.events import EventQueue, SourceEvent
from continuum.sources.lifecycle import ConnectorSyncLifecycle
from continuum.sources.provenance import utc_now_iso
from continuum.sources.slack.adapter import SlackAdapter

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "sources" / "slack"


@pytest.fixture(scope="module")
def hydradb_client():
    try:
        client = HydraDBClient()
        client.__enter__()
        client.health_check()
    except Exception as exc:
        pytest.skip(f"HydraDB required: {exc}")
    yield client
    client.__exit__(None, None, None)


def _worker(tmp_path: Path, client, *, reset_graph: bool = True) -> MemoryWorker:
    if reset_graph:
        delete_all_artifacts(client)
        wipe_for_entities(client, [])
    adapter = SlackAdapter(fixtures_dir=FIXTURES)
    lifecycle = ConnectorSyncLifecycle(adapter, cursor_path=tmp_path / "slack.cursor.json")
    return MemoryWorker(
        client=client,
        queue=EventQueue(tmp_path / "events.jsonl"),
        lifecycle=lifecycle,
        artifacts_path=tmp_path / "artifacts.jsonl",
        resolutions_path=tmp_path / "resolutions.json",
    )


@pytest.mark.hydradb
def test_memory_worker_ingests_fixture_event(tmp_path: Path, hydradb_client):
    worker = _worker(tmp_path, hydradb_client)
    native_id = "C07ACCT01:1728295000.500000"
    event = SourceEvent(
        event_id="evt-handoff",
        source="slack",
        event_type="message",
        native_id=native_id,
        payload={"event": {"channel": "C07ACCT01", "ts": "1728295000.500000"}},
        received_at=utc_now_iso(),
    )
    worker.queue.enqueue(event)
    results = worker.process_pending()
    assert len(results) == 1
    assert results[0].status == "processed"
    assert results[0].claims_loaded >= 1
    assert worker.resolutions_path.exists()


@pytest.mark.hydradb
def test_memory_worker_dedup_replay(tmp_path: Path, hydradb_client):
    worker = _worker(tmp_path, hydradb_client)
    native_id = "C07ACCT01:1728295000.500000"
    artifact = worker.lifecycle.fetch_record(native_id)
    assert artifact is not None
    first = worker.ingest_artifacts([artifact])
    assert first.claims_loaded >= 1
    second = worker.ingest_artifacts([artifact])
    assert second.status == "skipped"
    assert second.claims_loaded == 0


@pytest.mark.hydradb
def test_memory_worker_restart_same_resolutions(tmp_path: Path, hydradb_client):
    worker = _worker(tmp_path, hydradb_client, reset_graph=True)
    sync = worker.lifecycle.initial_sync(limit=5)
    worker.ingest_artifacts(sync.artifacts)
    resolutions_before = json.loads(worker.resolutions_path.read_text(encoding="utf-8"))

    restarted = MemoryWorker(
        client=hydradb_client,
        queue=EventQueue(tmp_path / "events.jsonl"),
        lifecycle=worker.lifecycle,
        artifacts_path=worker.artifacts_path,
        resolutions_path=worker.resolutions_path,
    )
    resolutions_after = json.loads(restarted.resolutions_path.read_text(encoding="utf-8"))
    assert resolutions_before.keys() == resolutions_after.keys()
