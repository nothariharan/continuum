#!/usr/bin/env python3
"""Run full-v1 baseline with frozen run IDs and resume support."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from continuum.eval.benchmark.baseline import ensure_graph_fixture, run_baseline
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, SYSTEMS
from continuum.hydradb import HydraDBClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", default="full-v1", choices=["sample-v1", "full-v1"])
    parser.add_argument("--answer-model", choices=["mock", "real"], default="real")
    parser.add_argument("--system", choices=[*SYSTEMS, "all"], default="all")
    parser.add_argument("--regression", action="store_true")
    parser.add_argument("--corpus-limit", type=int, default=0)
    parser.add_argument("--with-graph", action="store_true", default=True)
    parser.add_argument("--no-graph", action="store_true")
    parser.add_argument("--fail-on-fallback", action="store_true", default=True)
    parser.add_argument("--index-only", action="store_true")
    parser.add_argument("--skip-graph-setup", action="store_true")
    parser.add_argument("--root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    args = parser.parse_args()

    with_graph = args.with_graph and not args.no_graph
    system = None if args.system == "all" else args.system

    graph_client = None
    entity_store = None
    if with_graph and not args.index_only:
        if args.skip_graph_setup:
            client = HydraDBClient()
            client.health_check()
            from continuum.entities.store import EntityStore

            graph_client = client
            entity_store = EntityStore(client)
        else:
            graph_client, entity_store = ensure_graph_fixture()

    summary = run_baseline(
        mode=args.mode,
        run_id=args.run_id,
        answer_model=args.answer_model,
        with_graph=with_graph,
        system=system,
        regression=args.regression,
        corpus_limit=args.corpus_limit,
        fail_on_fallback=args.fail_on_fallback,
        index_only=args.index_only,
        root=args.root,
        graph_client=graph_client,
        entity_store=entity_store,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
