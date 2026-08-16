"""Entity-resolution evaluation runner (founder acceptance gate).

Usage:
    python scripts/eval_entity_resolution.py [--pairs FILE]

Reads identity-pairs.jsonl (gold labels + measured features), runs the
deterministic resolver over every pair, and reports the metrics that decide
whether the resolver may touch the graph. False-merge rate is the critical
number: a wrong merge contaminates the whole company graph.

Default fixture: data/fixtures/phase3/identity-pairs-tiny.json
Production input (teammate): data/entity_resolution/identity-pairs.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.entities.eval import evaluate_pairs
from continuum.entities.pairs import load_identity_pairs, load_teammate_identity_pairs
from continuum.entities.resolver import EntityResolver

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAIRS = ROOT / "data" / "fixtures" / "phase3" / "identity-pairs-tiny.jsonl"
REPORT_OUT = ROOT / "data" / "metadata" / "entity_resolution_eval.json"


def load_pairs_auto(path: Path) -> list:
    """Load pairs from either the founder (flat) or teammate (nested a/b) format."""
    first_line = path.open(encoding="utf-8").readline().strip()
    if first_line and '"a"' in first_line and '"b"' in first_line:
        return load_teammate_identity_pairs(path)
    return load_identity_pairs(path)


def main(pairs_path: Path, report_out: Path) -> int:
    pairs = load_pairs_auto(pairs_path)
    resolver = EntityResolver()
    report = evaluate_pairs(pairs, resolver)
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    m = report["metrics"]
    print(f"pairs: {report['pairs']}  gold: {report['gold_distribution']}")
    print(f"pair_accuracy        {m['pair_accuracy']}")
    print(f"SAME       precision {m['same_precision']}  recall {m['same_recall']}  f1 {m['same_f1']}")
    print(f"DIFFERENT  precision {m['different_precision']}  recall {m['different_recall']}  f1 {m['different_f1']}")
    print(f"FALSE MERGE RATE     {m['false_merge_rate']}  ({m['false_merge_count']} merges on non-SAME)")
    print(f"FALSE SPLIT RATE     {m['false_split_rate']}  ({m['false_split_count']} separates on SAME)")
    print(f"REVIEW rate          {m['review_rate']}  ABSTAIN rate {m['abstain_rate']}")
    print(f"decisions: {report['decision_distribution']}")
    print(f"error taxonomy: {report.get('error_taxonomy')}")
    print(f"\nwrote {report_out}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--report-out", type=Path, default=REPORT_OUT)
    args = parser.parse_args()
    raise SystemExit(main(args.pairs, args.report_out))
