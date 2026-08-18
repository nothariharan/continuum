#!/usr/bin/env python3
"""Expand identity-pair gold set scaffold toward 250+ pairs (BATCH G)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "labels" / "phase3-identity-pairs.jsonl"
TARGET = ROOT / "data" / "labels" / "phase3-identity-pairs-expanded.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-count", type=int, default=250)
    parser.add_argument("--out", type=Path, default=TARGET)
    args = parser.parse_args()

    rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) >= args.target_count:
        args.out.write_text("\n".join(json.dumps(r) for r in rows[: args.target_count]) + "\n", encoding="utf-8")
    else:
        # Scaffold: duplicate with synthetic variants until target (placeholder for manual labeling)
        expanded = list(rows)
        index = 0
        while len(expanded) < args.target_count:
            base = dict(rows[index % len(rows)])
            base["pair_id"] = f"{base.get('pair_id', 'ip')}-synthetic-{len(expanded)}"
            base["note"] = (base.get("note") or "") + " [synthetic scaffold — replace with labeled pair]"
            expanded.append(base)
            index += 1
        args.out.write_text("\n".join(json.dumps(r) for r in expanded) + "\n", encoding="utf-8")

    print(f"wrote {args.out} ({args.target_count} rows scaffold)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
