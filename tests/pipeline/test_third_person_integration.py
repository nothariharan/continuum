"""Batch 1 — third-person ingestion via the memory worker → graph → answer.

A third-person message ("Morgan owns Acme.") posted by someone else (author
"soham") must mint person:morgan from the body, load the OWNS claim, and
answer "Who owns Acme?" with Morgan. HydraDB-marked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from continuum.benchmark import answer
from continuum.dataset.artifact import Artifact
from continuum.hydradb import HydraDBClient
from continuum.hydradb.artifacts import delete_all_artifacts
from continuum.hydradb.claims import wipe_for_entities
from continuum.pipeline.memory_worker import MemoryWorker
from continuum.pipeline.source_e2e import format_answer_from_result
from continuum.sources.events import EventQueue
from continuum.sources.lifecycle import ConnectorSyncLifecycle
from continuum.sources.slack.adapter import SlackAdapter

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "sources" / "slack"


def _ask(client: HydraDBClient, question: str, entity: str) -> str:
    result = answer(
        client,
        {"question_id": "tp", "question": question, "evidence_entity": entity, "predicate": "OWNS"},
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
def test_third_person_message_ingests_and_answers(tmp_path: Path, hydradb_client):
    adapter = SlackAdapter(fixtures_dir=FIXTURES)
    lifecycle = ConnectorSyncLifecycle(adapter, cursor_path=tmp_path / "cursor.json")
    worker = MemoryWorker(
        client=hydradb_client,
        queue=EventQueue(tmp_path / "events.jsonl"),
        lifecycle=lifecycle,
        artifacts_path=tmp_path / "artifacts.jsonl",
        resolutions_path=tmp_path / "resolutions.json",
    )
    artifact = Artifact(
        id="dsid_3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a",
        source="slack",
        source_id="tp-1",
        type="slack_message",
        author="soham",
        timestamp="2026-08-01T00:00:00+00:00",
        title="t",
        content="Morgan owns Acme.",
        metadata={"participants": []},
    )
    result = worker.ingest_artifacts([artifact])
    assert result.status == "processed"
    assert result.claims_loaded >= 1

    resolutions = json.loads(worker.resolutions_path.read_text(encoding="utf-8"))
    assert "person:morgan" in resolutions

    got = _ask(hydradb_client, "Who owns Acme?", "account:acme")
    assert "Morgan" in got
