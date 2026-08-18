#!/usr/bin/env python3
"""Poll EventQueue and incrementally update Continuum graph memory."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from continuum.hydradb import HydraDBClient
from continuum.pipeline.memory_worker import DEFAULT_QUEUE, MemoryWorker
from continuum.sources.events import EventQueue
from continuum.sources.lifecycle import ConnectorSyncLifecycle
from continuum.sources.slack.adapter import SlackAdapter


def _build_lifecycle(mode: str, fixtures_dir: Path | None) -> ConnectorSyncLifecycle:
    token = os.environ.get("SLACK_BOT_TOKEN") if mode == "live" else None
    adapter = SlackAdapter(fixtures_dir=fixtures_dir, token=token)
    cursor_path = ROOT / "data" / "ingestion" / "slack.cursor.json"
    return ConnectorSyncLifecycle(adapter, cursor_path=cursor_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--mode", choices=("fixtures", "live"), default="fixtures")
    parser.add_argument("--fixtures-dir", type=Path, default=None)
    parser.add_argument("--once", action="store_true", help="process pending events once and exit")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    lifecycle = _build_lifecycle(args.mode, args.fixtures_dir)
    health = lifecycle.source_health()
    if not health.ok:
        raise SystemExit(f"Slack source unhealthy: {health.detail}")

    with HydraDBClient() as client:
        client.health_check()
        worker = MemoryWorker(
            client=client,
            queue=EventQueue(args.queue),
            lifecycle=lifecycle,
        )
        if args.once:
            results = worker.process_pending()
            for row in results:
                print(f"{row.event_id}\t{row.status}\t{row.claims_loaded}\t{row.detail}")
            return 0
        worker.run_forever(poll_seconds=args.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
