#!/usr/bin/env python3
"""Build identity-pair gold dataset v1 from legacy labels + hard-case enrichment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.eval.identity.candidates import build_identity_pairs_v1, generate_extended_candidates, label_distribution
from continuum.eval.identity.schema import DEFAULT_DATASET_PATH, write_identity_pairs

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_OUT = ROOT / "data" / "labels" / "phase3-identity-candidates-v1.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path for identity-pairs.jsonl (without features)",
    )
    parser.add_argument(
        "--candidates-output",
        type=Path,
        default=CANDIDATES_OUT,
        help="Extended unlabeled candidate pool",
    )
    parser.add_argument("--candidate-limit", type=int, default=500)
    args = parser.parse_args()

    rows = build_identity_pairs_v1()
    write_identity_pairs(rows, args.output)
    print(f"wrote {len(rows)} labeled pairs -> {args.output}")
    print("label distribution:", label_distribution(rows))

    candidates = generate_extended_candidates(limit=args.candidate_limit)
    args.candidates_output.parent.mkdir(parents=True, exist_ok=True)
    with args.candidates_output.open("w", encoding="utf-8") as handle:
        for pair in candidates:
            handle.write(json.dumps(pair, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(candidates)} candidate pairs -> {args.candidates_output}")


if __name__ == "__main__":
    main()
