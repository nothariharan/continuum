"""Extract mentions from normalized artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.extract.schemas import artifacts_from_dicts, load_artifacts_jsonl, write_jsonl
from continuum.extract.mention import extract_mentions, mentions_to_jsonl_rows

DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "extraction" / "mentions.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract mentions from artifact sample")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--method", choices=["deterministic", "llm", "hybrid"], default="deterministic")
    args = parser.parse_args()

    rows = load_artifacts_jsonl(args.sample)
    artifacts = artifacts_from_dicts(rows)
    mentions = extract_mentions(artifacts, method=args.method)
    count = write_jsonl(args.out, mentions_to_jsonl_rows(mentions))
    print(json.dumps({"mentions": count, "artifacts": len(artifacts), "method": args.method, "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
