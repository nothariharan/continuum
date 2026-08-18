#!/usr/bin/env python3
"""Initial Slack demo sync: ingest artifacts and load graph memory."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from continuum.hydradb import HydraDBClient
from continuum.pipeline.memory_worker import MemoryWorker
from continuum.sources.events import EventQueue
from continuum.sources.lifecycle import ConnectorSyncLifecycle, write_artifacts_jsonl
from continuum.sources.slack.adapter import SlackAdapter

DEFAULT_OUT = ROOT / "docs" / "slack-demo-initial-ingest.md"
INGESTION = ROOT / "data" / "ingestion"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fixtures", "live"), default="fixtures")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--report", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--reset-resolutions", action="store_true")
    args = parser.parse_args()

    import os

    token = os.environ.get("SLACK_BOT_TOKEN") if args.mode == "live" else None
    adapter = SlackAdapter(token=token)
    lifecycle = ConnectorSyncLifecycle(adapter, cursor_path=INGESTION / "slack.cursor.json")
    health = lifecycle.source_health()
    if not health.ok:
        raise SystemExit(f"Slack unhealthy: {health.detail}")

    artifacts_path = INGESTION / "slack-artifacts.jsonl"
    resolutions_path = INGESTION / "memory-resolutions.json"
    if args.reset_resolutions and resolutions_path.exists():
        resolutions_path.unlink()

    started = time.perf_counter()
    sync = lifecycle.initial_sync(limit=args.limit)
    write_artifacts_jsonl(sync.artifacts, artifacts_path, append=False)

    with HydraDBClient() as client:
        client.health_check()
        worker = MemoryWorker(
            client=client,
            queue=EventQueue(INGESTION / "slack-events.jsonl"),
            lifecycle=lifecycle,
            artifacts_path=artifacts_path,
            resolutions_path=resolutions_path,
        )
        result = worker.ingest_artifacts(sync.artifacts)

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    resolutions = json.loads(resolutions_path.read_text(encoding="utf-8")) if resolutions_path.exists() else {}

    lines = [
        "# Slack Demo — Initial Ingest",
        "",
        f"- mode: `{args.mode}`",
        f"- artifacts: **{len(sync.artifacts)}**",
        f"- claims loaded: **{result.claims_loaded}**",
        f"- entities: **{len(resolutions)}**",
        f"- duration_ms: **{duration_ms}**",
        "",
        "## Entity keys",
        "",
    ]
    for key in sorted(resolutions):
        lines.append(f"- `{key}` — {resolutions[key].get('name')}")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
