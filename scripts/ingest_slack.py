#!/usr/bin/env python3
"""Ingest Slack records into canonical Artifact JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.dataset.artifact import artifact_to_dict
from continuum.sources.cursor import SyncCursor
from continuum.sources.slack.adapter import SlackAdapter
from continuum.sources.sync import load_cursor, save_cursor

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "ingestion" / "slack-artifacts.jsonl"
DEFAULT_CURSOR = Path(__file__).resolve().parents[1] / "data" / "ingestion" / "slack.cursor.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Slack into canonical Artifacts")
    parser.add_argument("--mode", choices=("fixtures", "live"), default="fixtures")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cursor", type=Path, default=DEFAULT_CURSOR)
    parser.add_argument("--fixtures-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--incremental", action="store_true", help="append only records after cursor")
    args = parser.parse_args()

    adapter = SlackAdapter(fixtures_dir=args.fixtures_dir)
    adapter.authenticate()

    cursor: SyncCursor | None = None
    if args.incremental and args.cursor.exists():
        cursor = load_cursor(args.cursor)

    if args.mode == "fixtures" and not args.incremental:
        artifacts = adapter.normalize_all_fixtures()
    else:
        result = adapter.fetch(cursor=cursor, limit=args.limit)
        artifacts = [adapter.normalize(raw) for raw in result.records]
        if result.next_cursor:
            save_cursor(result.next_cursor, args.cursor)
        elif result.records:
            save_cursor(adapter.cursor(result.records[-1]), args.cursor)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.incremental else "w"
    with args.out.open(mode, encoding="utf-8") as handle:
        for artifact in artifacts:
            handle.write(json.dumps(artifact_to_dict(artifact), ensure_ascii=False) + "\n")

    print(f"wrote {len(artifacts)} artifact(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
