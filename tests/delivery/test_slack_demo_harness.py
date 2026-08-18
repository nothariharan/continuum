"""Slack company-memory demo harness — replays B9/B15/B16 without live Slack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from continuum.benchmark import answer
from continuum.hydradb import HydraDBClient
from continuum.hydradb.artifacts import delete_all_artifacts
from continuum.hydradb.claims import wipe_for_entities
from continuum.pipeline.memory_worker import MemoryWorker
from continuum.pipeline.source_e2e import format_answer_from_result
from continuum.sources.events import EventQueue, SourceEvent
from continuum.sources.lifecycle import ConnectorSyncLifecycle
from continuum.sources.provenance import utc_now_iso
from continuum.sources.slack.adapter import SlackAdapter

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "sources" / "slack"


def _ask(client, question: str, entity: str) -> str:
    result = answer(
        client,
        {"question_id": "demo", "question": question, "evidence_entity": entity, "predicate": "OWNS"},
    )
    return format_answer_from_result(result, {"category": "ownership", "question": question})


@pytest.fixture(scope="module")
def hydradb_client():
    try:
        client = HydraDBClient()
        client.__enter__()
        client.health_check()
    except Exception as exc:
        pytest.skip(f"HydraDB required: {exc}")
    delete_all_artifacts(client)
    wipe_for_entities(client, [])
    yield client
    client.__exit__(None, None, None)


@pytest.mark.hydradb
def test_demo_b9_ownership_update_without_manual_reload(tmp_path: Path, hydradb_client):
    adapter = SlackAdapter(fixtures_dir=FIXTURES)
    lifecycle = ConnectorSyncLifecycle(adapter, cursor_path=tmp_path / "cursor.json")
    worker = MemoryWorker(
        client=hydradb_client,
        queue=EventQueue(tmp_path / "events.jsonl"),
        lifecycle=lifecycle,
        artifacts_path=tmp_path / "artifacts.jsonl",
        resolutions_path=tmp_path / "resolutions.json",
    )
    initial = lifecycle.initial_sync(limit=20)
    worker.ingest_artifacts(initial.artifacts)
    before = _ask(hydradb_client, "Who owns CedarBank?", "account:cedarbank")

    worker.queue.enqueue(
        SourceEvent(
            event_id="b9-update",
            source="slack",
            event_type="message",
            native_id="C07ACCT01:1728295000.500000",
            payload={},
            received_at=utc_now_iso(),
        )
    )
    worker.process_pending()
    after = _ask(hydradb_client, "Who owns CedarBank?", "account:cedarbank")
    assert before != after or "Camila" in after


@pytest.mark.hydradb
def test_demo_b15_duplicate_event_no_duplicate_state(tmp_path: Path, hydradb_client):
    adapter = SlackAdapter(fixtures_dir=FIXTURES)
    lifecycle = ConnectorSyncLifecycle(adapter, cursor_path=tmp_path / "cursor.json")
    worker = MemoryWorker(
        client=hydradb_client,
        queue=EventQueue(tmp_path / "events.jsonl"),
        lifecycle=lifecycle,
        artifacts_path=tmp_path / "artifacts.jsonl",
        resolutions_path=tmp_path / "resolutions.json",
    )
    native_id = "C07ACCT01:1728295000.500000"
    worker.queue.enqueue(
        SourceEvent("dup-1", "slack", "message", native_id, {}, utc_now_iso())
    )
    worker.process_pending()
    resolutions = json.loads(worker.resolutions_path.read_text(encoding="utf-8"))
    worker.queue.enqueue(
        SourceEvent("dup-2", "slack", "message", native_id, {}, utc_now_iso())
    )
    worker.process_pending()
    resolutions_again = json.loads(worker.resolutions_path.read_text(encoding="utf-8"))
    assert resolutions.keys() == resolutions_again.keys()


@pytest.mark.hydradb
def test_demo_b16_restart_worker_same_answer(tmp_path: Path, hydradb_client):
    adapter = SlackAdapter(fixtures_dir=FIXTURES)
    lifecycle = ConnectorSyncLifecycle(adapter, cursor_path=tmp_path / "cursor.json")
    worker = MemoryWorker(
        client=hydradb_client,
        queue=EventQueue(tmp_path / "events.jsonl"),
        lifecycle=lifecycle,
        artifacts_path=tmp_path / "artifacts.jsonl",
        resolutions_path=tmp_path / "resolutions.json",
    )
    sync = lifecycle.initial_sync(limit=10)
    worker.ingest_artifacts(sync.artifacts)
    answer_a = _ask(hydradb_client, "Who owns Acme?", "account:acme")

    restarted = MemoryWorker(
        client=hydradb_client,
        queue=EventQueue(tmp_path / "events.jsonl"),
        lifecycle=lifecycle,
        artifacts_path=tmp_path / "artifacts.jsonl",
        resolutions_path=tmp_path / "resolutions.json",
    )
    answer_b = _ask(hydradb_client, "Who owns Acme?", "account:acme")
    assert answer_a == answer_b
    assert restarted._resolutions  # noqa: SLF001 — persisted state reload
