"""Build Continuum Gold Benchmark v1 from the Phase 2A sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.eval.gold_v1 import (
    DEFAULT_GOLD_ROOT,
    DEFAULT_LEGACY_LABELS,
    DEFAULT_SAMPLE,
    build_gold_benchmark,
    validate_gold_benchmark,
    write_gold_benchmark,
)

DEFAULT_OUT = DEFAULT_GOLD_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Gold Benchmark v1")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--legacy-labels", type=Path, default=DEFAULT_LEGACY_LABELS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--seed", type=int, default=20260816)
    args = parser.parse_args()

    benchmark = build_gold_benchmark(
        sample_path=args.sample,
        legacy_labels_path=args.legacy_labels,
        count=args.count,
        seed=args.seed,
    )
    errors = validate_gold_benchmark(benchmark)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1

    paths = write_gold_benchmark(benchmark, args.out)
    print(
        json.dumps(
            {
                "ok": True,
                "manifest": benchmark.manifest,
                "paths": {key: str(path) for key, path in paths.items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
