"""Run a versioned extraction evaluation against Gold Benchmark v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.eval.experiment import DEFAULT_EVAL_ROOT, DEFAULT_GOLD_ROOT, run_extraction_eval

DEFAULT_RUN = "001"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Gold Benchmark v1 extraction eval")
    parser.add_argument("--run", default=DEFAULT_RUN, help="run id, e.g. 001 or run_001")
    parser.add_argument(
        "--strategy",
        choices=["deterministic", "hybrid", "llm"],
        default="deterministic",
    )
    parser.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    parser.add_argument("--eval-root", type=Path, default=DEFAULT_EVAL_ROOT)
    parser.add_argument(
        "--write-predictions",
        action="store_true",
        help="write predictions/ under run dir (off by default for git hygiene)",
    )
    args = parser.parse_args()

    report = run_extraction_eval(
        run_id=args.run,
        strategy=args.strategy,
        gold_root=args.gold_root,
        eval_root=args.eval_root,
        write_predictions=args.write_predictions,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
