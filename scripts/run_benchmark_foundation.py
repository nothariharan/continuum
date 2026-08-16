#!/usr/bin/env python3
"""Run the four-system benchmark foundation harness."""

from __future__ import annotations

import argparse
from pathlib import Path

from continuum.eval.benchmark.runner import run_benchmark, trace_question
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["sample-v1", "full-v1"], default="sample-v1")
    parser.add_argument("--answer-model", choices=["mock", "real"], default="mock")
    parser.add_argument("--with-graph", action="store_true")
    parser.add_argument("--regression", action="store_true")
    parser.add_argument("--trace", type=str, default="")
    parser.add_argument("--root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument(
        "--corpus-limit",
        type=int,
        default=0,
        help="Limit full-v1 corpus records for smoke runs (0 = all)",
    )
    args = parser.parse_args()

    if args.trace:
        print(
            trace_question(
                args.trace,
                mode=args.mode,
                answer_model=args.answer_model,
                with_graph=args.with_graph,
                root=args.root,
            )
        )
        return

    comparison = run_benchmark(
        args.mode,
        answer_model=args.answer_model,
        with_graph=args.with_graph,
        root=args.root,
        regression=args.regression,
        corpus_limit=args.corpus_limit,
    )
    print(f"mode={comparison['corpus_mode']} questions={comparison['question_count']} "
          f"official_benchmark={comparison['official_benchmark']}")
    for system, scores in comparison["official_score"].items():
        print(f"  {system}: {scores}")


if __name__ == "__main__":
    main()
