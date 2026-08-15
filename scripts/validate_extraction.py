"""Validate mentions.jsonl and claims.jsonl against contract v1 and the artifact sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.eval.validate import validate_extraction_outputs

DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_MENTIONS = Path(__file__).resolve().parents[1] / "data" / "extraction" / "mentions.jsonl"
DEFAULT_CLAIMS = Path(__file__).resolve().parents[1] / "data" / "extraction" / "claims.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "metadata" / "extraction_validation.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 2B extraction outputs")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--mentions", type=Path, default=DEFAULT_MENTIONS)
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check-spans", action="store_true")
    args = parser.parse_args()

    report = validate_extraction_outputs(
        sample_path=args.sample,
        mentions_path=args.mentions,
        claims_path=args.claims,
        check_spans=args.check_spans,
    )
    payload = report.to_dict()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
