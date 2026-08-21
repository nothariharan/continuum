#!/usr/bin/env python3
"""Three-stage ownership demo driver — drives the SAME canonical memory the
Slack bot reads, so `@continuum who owns Acme?` reflects each stage live.

    python scripts/demo_owner.py default   # Morgan owns Acme  (clean start)
    python scripts/demo_owner.py priya     # Priya owns   (Previously: Morgan)
    python scripts/demo_owner.py hari      # Hari owns    (Previously: Priya, Morgan)

Run them in order for the demo; `default` resets back to Morgan for the next take.
Use --owner to change the final owner name (default: Hari).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run-as-script safety: repo root importable (extraction imports scripts.*).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _ingest_takeover(client, owner: str) -> None:
    """Ingest a plaintext 'I'm taking over Acme' by `owner` → owner OWNS Acme."""
    from datetime import UTC, datetime

    from continuum.pipeline.memory_worker import MemoryWorker
    from continuum.sources.events import EventQueue
    from continuum.sources.slack.models import SlackMessage
    from continuum.sources.slack.normalize import normalize_slack_message

    now = datetime.now(UTC)
    msg = SlackMessage(
        ts=f"{now.timestamp():.6f}",
        channel_id="C_OWNERSHIP",
        channel_name="ownership",
        text="I'm taking over Acme ownership",
        user_id=f"U_{owner.upper().replace(' ', '_')}",
        user_display=owner,
        username=owner.lower().replace(" ", "."),
    )
    artifact = normalize_slack_message(msg, ingested_at=now.isoformat())
    worker = MemoryWorker(
        client=client,
        queue=EventQueue(path=Path("data/ingestion/slack-events.jsonl")),
        lifecycle=None,
    )
    worker.ingest_artifacts([artifact])


def _show(client) -> None:
    """Print exactly what Slack will say for 'who owns Acme now?'."""
    from continuum.delivery.query_service import QueryService
    from continuum.delivery.slack_bot import SlackQueryBot
    from continuum.delivery.slack_formatter import format_slack_answer

    result = QueryService(client).ask("who owns Acme now?")
    SlackQueryBot(client)._enrich_history(result)  # attach prior owners
    print("--- @continuum who owns Acme? ---")
    print(format_slack_answer(result)["text"].encode("ascii", "replace").decode())


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("stage", choices=("default", "priya", "hari"))
    parser.add_argument("--owner", default="Hari", help="final owner name for the 'hari' stage")
    args = parser.parse_args()

    from continuum.hydradb.config import _load_dotenv

    _load_dotenv()

    import scripts.demo_golden_path as gp
    from continuum.hydradb import HydraDBClient
    from continuum.hydradb.claims import wipe_for_entities

    client = HydraDBClient()
    client.health_check()
    scenario = gp.load_scenario()

    if args.stage == "default":
        gp.reset(client, scenario)
        wipe_for_entities(client, ["person:hari", "person:hariharan", f"person:{args.owner.lower()}"])
        gp.seed(client, scenario)  # Slack: "Morgan owns Acme"
        print("[stage] default -> Morgan owns Acme")
    elif args.stage == "priya":
        gp.apply(client, scenario, "gmail-aug5")  # Gmail transition + Aug-5 correction
        print("[stage] priya -> Priya owns Acme (effective Aug 5)")
    elif args.stage == "hari":
        _ingest_takeover(client, args.owner)
        print(f"[stage] hari -> {args.owner} owns Acme (live takeover)")

    _show(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
