"""Incremental company-memory worker — EventQueue → graph updates."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from continuum.dataset.artifact import Artifact
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import artifact_source_fixture, artifact_to_claim_fixture, load_claims
from continuum.pipeline.source_e2e import (
    claim_dict_to_model,
    extract_claim_records,
    gate_claims_for_load,
    resolve_entities_from_artifacts,
)
from continuum.sources.events import EventQueue, SourceEvent
from continuum.sources.lifecycle import ConnectorSyncLifecycle, write_artifacts_jsonl

logger = logging.getLogger(__name__)

DEFAULT_QUEUE = Path("data/ingestion/slack-events.jsonl")
DEFAULT_ARTIFACTS = Path("data/ingestion/slack-artifacts.jsonl")
DEFAULT_RESOLUTIONS = Path("data/ingestion/memory-resolutions.json")


@dataclass(frozen=True)
class MemoryWorkerResult:
    event_id: str
    status: str
    artifact_id: str | None = None
    claims_loaded: int = 0
    detail: str = ""


@dataclass
class MemoryWorker:
    """Process queued source events into incremental HydraDB memory."""

    client: HydraDBClient
    queue: EventQueue
    lifecycle: ConnectorSyncLifecycle
    artifacts_path: Path = DEFAULT_ARTIFACTS
    resolutions_path: Path = DEFAULT_RESOLUTIONS
    refinement_provider: str = "mock"
    _resolutions: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)
    _seen_artifacts: set[str] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        self._resolutions = self._load_resolutions()
        if self.artifacts_path.exists():
            for line in self.artifacts_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                self._seen_artifacts.add(row["id"])

    def _load_resolutions(self) -> dict[str, dict[str, Any]]:
        if not self.resolutions_path.exists():
            return {}
        return json.loads(self.resolutions_path.read_text(encoding="utf-8"))

    def _persist_resolutions(self) -> None:
        self.resolutions_path.parent.mkdir(parents=True, exist_ok=True)
        self.resolutions_path.write_text(
            json.dumps(self._resolutions, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def ingest_artifacts(self, artifacts: list[Artifact]) -> MemoryWorkerResult:
        fresh = [a for a in artifacts if a.id not in self._seen_artifacts]
        if not fresh:
            return MemoryWorkerResult(event_id="", status="skipped", detail="no new artifacts")

        new_res, entities = resolve_entities_from_artifacts(fresh)
        self._resolutions.update(new_res)
        claims, _stats = extract_claim_records(
            fresh,
            self._resolutions,
            refinement_provider=self.refinement_provider,
        )
        loadable, rejected = gate_claims_for_load(claims, self._resolutions, fresh)
        if loadable:
            fixture_artifacts = [artifact_to_claim_fixture(a) for a in fresh]
            sources: dict[str, dict[str, Any]] = {}
            for artifact in fresh:
                source = artifact_source_fixture(artifact)
                sources[source["key"]] = source
            load_claims(
                self.client,
                claims=[claim_dict_to_model(row) for row in loadable],
                resolutions=self._resolutions,
                fixture_artifacts=fixture_artifacts,
                fixture_sources=list(sources.values()),
                reset=False,
            )
            EntityStore(self.client).save(entities, reset=False)

        write_artifacts_jsonl(fresh, self.artifacts_path, append=True)
        for artifact in fresh:
            self._seen_artifacts.add(artifact.id)
        self._persist_resolutions()

        logger.info(
            "memory_ingest artifact_count=%s claims_loaded=%s rejected=%s",
            len(fresh),
            len(loadable),
            len(rejected),
        )
        return MemoryWorkerResult(
            event_id="",
            status="processed",
            artifact_id=fresh[0].id if fresh else None,
            claims_loaded=len(loadable),
            detail=f"{len(fresh)} artifact(s), {len(rejected)} rejected",
        )

    def process_event(self, event: SourceEvent) -> MemoryWorkerResult:
        if event.status != "pending":
            return MemoryWorkerResult(event.event_id, "skipped", detail=f"status={event.status}")

        native_id = event.native_id
        if not native_id:
            channel = (event.payload.get("event") or {}).get("channel")
            ts = (event.payload.get("event") or {}).get("ts")
            if channel and ts:
                native_id = f"{channel}:{ts}"
        if not native_id:
            self.queue.mark_processed(event.event_id, status="failed")
            return MemoryWorkerResult(event.event_id, "failed", detail="missing native_id")

        artifact = self.lifecycle.fetch_record(native_id)
        if artifact is None:
            self.queue.mark_processed(event.event_id, status="failed")
            return MemoryWorkerResult(event.event_id, "failed", detail="record not found")

        result = self.ingest_artifacts([artifact])
        self.queue.mark_processed(event.event_id, status="processed" if result.status == "processed" else "failed")
        return MemoryWorkerResult(
            event_id=event.event_id,
            status=result.status,
            artifact_id=result.artifact_id,
            claims_loaded=result.claims_loaded,
            detail=result.detail,
        )

    def process_pending(self, *, limit: int = 50) -> list[MemoryWorkerResult]:
        results: list[MemoryWorkerResult] = []
        pending = [event for event in self.queue.load() if event.status == "pending"]
        for event in pending[:limit]:
            results.append(self.process_event(event))
        return results

    def run_forever(self, *, poll_seconds: float = 2.0) -> None:
        logger.info("memory_worker started queue=%s", self.queue.path)
        while True:
            batch = self.process_pending()
            if batch:
                for row in batch:
                    logger.info(
                        "memory_event event_id=%s status=%s claims=%s",
                        row.event_id,
                        row.status,
                        row.claims_loaded,
                    )
            time.sleep(poll_seconds)
