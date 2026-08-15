"""Write top-N claims from claims.jsonl for founder checkpoint #2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_IN = Path(__file__).resolve().parents[1] / "data" / "extraction" / "claims.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "extraction" / "claims_checkpoint50.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Slice top claims by confidence")
    parser.add_argument("--in", dest="input_path", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.sort(key=lambda row: (-row["confidence"], row["artifact_id"], row["predicate"]))
    selected = rows[: args.limit]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selected), encoding="utf-8")
    print(json.dumps({"claims": len(selected), "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
