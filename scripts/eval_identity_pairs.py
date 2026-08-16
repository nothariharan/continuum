#!/usr/bin/env python3
"""Write identity-pair gold dataset coverage report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.eval.identity.report import DEFAULT_REPORT_PATH, write_identity_pairs_report
from continuum.eval.identity.schema import DEFAULT_DATASET_PATH, load_identity_pairs, validate_identity_pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    rows = load_identity_pairs(args.input)
    errors = validate_identity_pairs(rows, require_features=True)
    if errors:
        raise SystemExit("dataset validation failed:\n- " + "\n- ".join(errors))

    report_path = write_identity_pairs_report(rows, args.output)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    print(f"wrote report -> {report_path}")
    print("pair_count:", report["pair_count"])
    print("label_distribution:", report["label_distribution"])


if __name__ == "__main__":
    main()
