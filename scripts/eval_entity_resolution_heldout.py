"""Seeded calibration/evaluation split over the real identity pairs (Phase 3B).

Splits the 103-pair dataset into a calibration subset (threshold selection)
and a held-out evaluation subset, preserving label distribution. Runs the
real resolver (frozen thresholds) over both and reports metrics separately.

The dataset is small (103 pairs): the split is a methodological exercise and
the held-out numbers carry wide error bars. This is stated explicitly rather
than pretending it is a production benchmark.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from continuum.entities.eval import EntityResolutionEval
from continuum.entities.pairs import load_teammate_identity_pairs
from continuum.entities.resolver import EntityResolver

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAIRS = ROOT / "data" / "entity_resolution" / "v1" / "identity-pairs.jsonl"
DEFAULT_OUT = ROOT / "data" / "metadata" / "entity_resolution_heldout_eval.json"


def split_pairs(pairs, seed: int = 42, eval_fraction: float = 0.30):
    rng = random.Random(seed)
    by_label: dict[str, list] = {}
    for pair in pairs:
        by_label.setdefault(pair.label, []).append(pair)
    calibration, evaluation = [], []
    for label, group in by_label.items():
        rng.shuffle(group)
        n_eval = max(1, round(len(group) * eval_fraction))
        evaluation.extend(group[:n_eval])
        calibration.extend(group[n_eval:])
    rng.shuffle(calibration)
    rng.shuffle(evaluation)
    return calibration, evaluation


def main(pairs_path: Path, report_out: Path, seed: int, eval_fraction: float) -> dict:
    pairs = load_teammate_identity_pairs(pairs_path)
    calibration, evaluation = split_pairs(pairs, seed=seed, eval_fraction=eval_fraction)

    resolver = EntityResolver()  # frozen default thresholds (0.90)
    cal_report = EntityResolutionEval(calibration).run(resolver)
    eval_report = EntityResolutionEval(evaluation).run(resolver)

    report = {
        "gate": "entity-resolution-heldout-eval",
        "dataset": str(pairs_path),
        "seed": seed,
        "eval_fraction": eval_fraction,
        "note": "small dataset (103 pairs): held-out numbers carry wide error bars",
        "split": {
            "calibration": len(calibration),
            "evaluation": len(evaluation),
            "calibration_labels": dict(Counter(p.label for p in calibration)),
            "evaluation_labels": dict(Counter(p.label for p in evaluation)),
        },
        "calibration_metrics": cal_report["metrics"],
        "evaluation_metrics": eval_report["metrics"],
        "calibration_rows": cal_report["rows"],
        "evaluation_rows": eval_report["rows"],
    }
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"split: calibration={len(calibration)} evaluation={len(evaluation)} "
          f"seed={seed} eval_fraction={eval_fraction}")
    print(f"calibration labels: {dict(Counter(p.label for p in calibration))}")
    print(f"evaluation labels:  {dict(Counter(p.label for p in evaluation))}")
    print()
    for label, r in (("calibration", cal_report["metrics"]), ("evaluation", eval_report["metrics"])):
        print(f"[{label}] accuracy={r['pair_accuracy']} FM={r['false_merge_rate']} "
              f"FS={r['false_split_rate']} SAME_F1={r['same_f1']} DIFF_F1={r['different_f1']} "
              f"review={r['review_rate']} abstain={r['abstain_rate']}")
    print(f"\nwrote {report_out}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-fraction", type=float, default=0.30)
    args = parser.parse_args()
    raise SystemExit(main(args.pairs, args.report_out, args.seed, args.eval_fraction))
