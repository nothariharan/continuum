#!/usr/bin/env python3
"""Ingest a single plaintext Slack-style message into live company memory.

Demo bridge: turns a natural-language line like

    "I'm taking over Acme ownership"

posted by a given author into a real OWNS claim (author -> Acme) via the SAME
canonical incremental pipeline the memory worker uses. After this runs,
`@continuum who owns Acme?` reflects the new owner.

    python scripts/ingest_message.py --author "Hariharan" --text "I'm taking over Acme ownership"

Recognised author-ownership phrasings (subject = the author):
    "taking over <Account>"      e.g. "I'm taking over Acme"
    "handing off <Account>"      e.g. "handing off Acme"
    "still own <Account>"        e.g. "I still own Acme"
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

# Run-as-script safety: ensure the repo root is importable so the extraction
# pipeline can import `scripts.checkpoint_claims`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", required=True, help="Display name of the message author (becomes the owner)")
    parser.add_argument("--text", required=True, help="The message body, e.g. \"I'm taking over Acme ownership\"")
    parser.add_argument("--channel", default="ownership", help="Channel name (cosmetic)")
    args = parser.parse_args()

    from continuum.hydradb.config import _load_dotenv

    _load_dotenv()

    from continuum.delivery.query_service import QueryService
    from continuum.hydradb import HydraDBClient
    from continuum.pipeline.memory_worker import MemoryWorker
    from continuum.sources.events import EventQueue
    from continuum.sources.slack.models import SlackMessage
    from continuum.sources.slack.normalize import normalize_slack_message

    client = HydraDBClient()
    client.health_check()

    now = datetime.now(UTC)
    msg = SlackMessage(
        ts=f"{now.timestamp():.6f}",
        channel_id=f"C_{args.channel.upper()}",
        channel_name=args.channel,
        text=args.text,
        user_id=f"U_{args.author.upper().replace(' ', '_')}",
        user_display=args.author,
        username=args.author.lower().replace(" ", "."),
    )
    artifact = normalize_slack_message(msg, ingested_at=now.isoformat())

    worker = MemoryWorker(
        client=client,
        queue=EventQueue(path=Path("data/ingestion/slack-events.jsonl")),
        lifecycle=None,
    )
    result = worker.ingest_artifacts([artifact])

    owner = (QueryService(client).ask("who owns Acme now?").get("state_result") or {}).get("value") or {}
    print(f"ingested: {result.status}  claims_loaded={result.claims_loaded}  ({result.detail})")
    print(f"current owner of Acme -> {owner.get('name')}")
    if result.claims_loaded == 0:
        print("note: no ownership claim extracted — use a recognised phrasing like "
              "\"I'm taking over Acme\" (see --help).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
