"""Build entity-resolution mention inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.extract.inventory import aggregate_cross_source_signals, build_mention_inventory
from continuum.extract.schemas import mention_from_dict, read_jsonl

DEFAULT_IN = Path(__file__).resolve().parents[1] / "data" / "extraction" / "mentions.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "extraction" / "mention_inventory.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build mention inventory for entity resolution prep")
    parser.add_argument("--mentions", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    mentions = [mention_from_dict(row) for row in read_jsonl(args.mentions)]
    inventory = build_mention_inventory(mentions)
    signals = aggregate_cross_source_signals(mentions)
    payload = {"summary": signals, "entries": inventory, "entry_count": len(inventory)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"entries": len(inventory), "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
