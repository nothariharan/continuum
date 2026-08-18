#!/usr/bin/env python3
"""Unified source ingestion orchestrator."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from continuum.sources.gmail.adapter import GmailAdapter
from continuum.sources.lifecycle import ConnectorSyncLifecycle, write_artifacts_jsonl
from continuum.sources.slack.adapter import SlackAdapter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "ingestion"


def _adapter(source: str, *, mode: str, fixtures_dir: Path | None):
    if source == "slack":
        token = os.environ.get("SLACK_BOT_TOKEN") if mode == "live" else None
        return SlackAdapter(fixtures_dir=fixtures_dir, token=token)
    if source == "gmail":
        creds = os.environ.get("GMAIL_CREDENTIALS_PATH") if mode == "live" else None
        return GmailAdapter(fixtures_dir=fixtures_dir, credentials_path=creds)
    raise ValueError(f"unsupported source: {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("slack", "gmail"), required=True)
    parser.add_argument("--mode", choices=("fixtures", "live"), default="fixtures")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--cursor", type=Path, default=None)
    parser.add_argument("--fixtures-dir", type=Path, default=None)
    args = parser.parse_args()

    out = args.out or (DEFAULT_OUT / f"{args.source}-artifacts.jsonl")
    cursor_path = args.cursor or (DEFAULT_OUT / f"{args.source}.cursor.json")

    connector = _adapter(args.source, mode=args.mode, fixtures_dir=args.fixtures_dir)
    lifecycle = ConnectorSyncLifecycle(connector, cursor_path=cursor_path)

    health = lifecycle.source_health()
    if not health.ok:
        raise SystemExit(f"source health failed: {health.detail}")

    if args.incremental:
        result = lifecycle.incremental_sync(limit=args.limit)
    else:
        result = lifecycle.initial_sync(limit=args.limit)

    write_artifacts_jsonl(result.artifacts, out, append=args.incremental)
    print(f"wrote {len(result.artifacts)} artifact(s) -> {out}")
    if result.next_cursor:
        print(f"cursor: {result.next_cursor.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
