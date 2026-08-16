"""Resolver calibration harness — threshold sweep (Phase 3B).

Sweeps the resolver's decision thresholds over a gold identity-pair set and
reports the operating curve:

    MERGE threshold | false merge | false split | review | abstain | accuracy

The chosen operating point must minimize false merges (a wrong merge
contaminates the whole graph) while keeping useful coverage. This is the
tool that consumes the teammate's labeled identity-pairs.jsonl the moment
it lands.

Usage:
    python scripts/calibrate_entity_resolution.py \
        [--pairs data/fixtures/phase3/identity-pairs-tiny.jsonl]
        [--merge-min 0.80 --merge-max 0.97 --merge-step 0.01]

The resolver's own thresholds are NOT modified — only the sweep's
decision cutoffs. Existing defaults stay the safe hand-designed point.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from continuum.entities import ResolutionDecision
from continuum.entities.models import ResolutionVerdict
from continuum.entities.pairs import IdentityPair, load_identity_pairs, load_teammate_identity_pairs
from continuum.entities.resolver import EntityResolver

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAIRS = ROOT / "data" / "fixtures" / "phase3" / "identity-pairs-tiny.jsonl"
DEFAULT_REPORT_OUT = ROOT / "data" / "metadata" / "entity_resolution_calibration.json"


@dataclass
class SweepPoint:
    merge_threshold: float
    false_merge_rate: float
    false_merge_count: int
    false_split_rate: float
    false_split_count: int
    review_rate: float
    abstain_rate: float
    accuracy: float
    merge_count: int
    separate_count: int

    def to_dict(self) -> dict:
        return {
            "merge_threshold": round(self.merge_threshold, 3),
            "false_merge_rate": round(self.false_merge_rate, 4),
            "false_merge_count": self.false_merge_count,
            "false_split_rate": round(self.false_split_rate, 4),
            "false_split_count": self.false_split_count,
            "review_rate": round(self.review_rate, 4),
            "abstain_rate": round(self.abstain_rate, 4),
            "accuracy": round(self.accuracy, 4),
            "merge_count": self.merge_count,
            "separate_count": self.separate_count,
        }


class SweepingResolver(EntityResolver):
    """EntityResolver whose MERGE cutoff is overridable per run.

    Everything else (KEEP_SEPARATE rules, REVIEW tier, ABSTAIN, role-mailbox
    guard) is the real resolver's logic — only the merge threshold varies.
    """

    def __init__(self, merge_threshold: float = 0.90) -> None:
        super().__init__(merge_threshold=merge_threshold)


def sweep(
    pairs: list[IdentityPair],
    *,
    merge_min: float = 0.80,
    merge_max: float = 0.97,
    merge_step: float = 0.01,
) -> list[SweepPoint]:
    """Evaluate the resolver across MERGE thresholds."""
    from continuum.entities.eval import EntityResolutionEval

    points = []
    threshold = merge_min
    while threshold <= merge_max + 1e-9:
        resolver = SweepingResolver(merge_threshold=threshold)
        report = EntityResolutionEval(pairs).run(resolver)
        m = report["metrics"]
        points.append(
            SweepPoint(
                merge_threshold=threshold,
                false_merge_rate=m["false_merge_rate"],
                false_merge_count=m["false_merge_count"],
                false_split_rate=m["false_split_rate"],
                false_split_count=m["false_split_count"],
                review_rate=m["review_rate"],
                abstain_rate=m["abstain_rate"],
                accuracy=m["pair_accuracy"],
                merge_count=m.get("merge_count", report["decision_distribution"].get("MERGE", 0)),
                separate_count=report["decision_distribution"].get("KEEP_SEPARATE", 0),
            )
        )
        threshold = round(threshold + merge_step, 3)
    return points


def load_pairs_auto(path: Path) -> list[IdentityPair]:
    first_line = path.open(encoding="utf-8").readline().strip()
    if first_line and '"a"' in first_line and '"b"' in first_line:
        return load_teammate_identity_pairs(path)
    return load_identity_pairs(path)


def main(pairs_path: Path, report_out: Path) -> dict:
    pairs = load_pairs_auto(pairs_path)
    points = sweep(pairs)
    report = {
        "gate": "entity-resolution-calibration",
        "pairs": len(pairs),
        "gold_distribution": _gold_counts(pairs),
        "operating_curve": [p.to_dict() for p in points],
    }
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"pairs: {len(pairs)}  gold: {_gold_counts(pairs)}")
    print(f"{'MERGE':>6}  {'FM rate':>8}  {'FM':>3}  {'FS rate':>8}  {'FS':>3}  "
          f"{'REVIEW':>7}  {'ABSTAIN':>7}  {'ACC':>6}")
    for p in points:
        print(f"{p.merge_threshold:>6.2f}  {p.false_merge_rate:>8.4f}  {p.false_merge_count:>3}  "
              f"{p.false_split_rate:>8.4f}  {p.false_split_count:>3}  {p.review_rate:>7.4f}  "
              f"{p.abstain_rate:>7.4f}  {p.accuracy:>6.4f}")
    print(f"\nwrote {report_out}")
    return report


def _gold_counts(pairs: list[IdentityPair]) -> dict[str, int]:
    from collections import Counter

    return dict(Counter(p.label for p in pairs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_OUT)
    parser.add_argument("--merge-min", type=float, default=0.80)
    parser.add_argument("--merge-max", type=float, default=0.97)
    parser.add_argument("--merge-step", type=float, default=0.01)
    args = parser.parse_args()
    raise SystemExit(main(args.pairs, args.report_out))
