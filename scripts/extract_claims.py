"""Extract claims from normalized artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.extract.claim import claims_to_jsonl_rows, extract_claims
from continuum.extract.llm_client import load_local_env
from continuum.extract.schemas import artifacts_from_dicts, load_artifacts_jsonl, write_jsonl

DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "extraction" / "claims.jsonl"


def main() -> int:
    load_local_env()
    parser = argparse.ArgumentParser(description="Extract claims from artifact sample")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--method", choices=["deterministic", "llm", "hybrid"], default="deterministic")
    parser.add_argument("--min-confidence", type=float, default=0.70)
    parser.add_argument("--limit", type=int, default=0, help="limit output rows (0 = all)")
    args = parser.parse_args()

    rows = load_artifacts_jsonl(args.sample)
    artifacts = artifacts_from_dicts(rows)
    claims = extract_claims(artifacts, method=args.method)
    claims = [c for c in claims if c.confidence >= args.min_confidence]
    claims.sort(key=lambda c: (-c.confidence, c.artifact_id, c.predicate))
    if args.limit:
        claims = claims[: args.limit]
    count = write_jsonl(args.out, claims_to_jsonl_rows(claims))
    print(json.dumps({"claims": count, "artifacts": len(artifacts), "method": args.method, "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
