"""Generate the Phase 2A data-quality report over the normalized sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.dataset.quality import quality_report, quality_to_dict

DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "metadata" / "data_quality_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Data-quality report for the Phase 2A sample")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--scan-cap", type=int, default=400)
    args = parser.parse_args()

    sample_file = args.sample / "phase2a-sample.jsonl"
    report_file = args.sample / "phase2a-sample-report.json"

    records = []
    with sample_file.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    sample_meta = json.loads(report_file.read_text(encoding="utf-8"))
    rejected = sample_meta.get("rejected_detail", [])

    report = quality_report(records, rejected, scan_cap=args.scan_cap)
    payload = quality_to_dict(report)
    payload["sample_sha256"] = sample_meta.get("sha256")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())