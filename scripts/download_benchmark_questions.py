#!/usr/bin/env python3
"""Download pinned EnterpriseRAG-Bench question assets."""

from __future__ import annotations

import argparse
from pathlib import Path

from continuum.dataset.download import download_extra_questions_jsonl, download_questions_jsonl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "data" / "raw"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--extra", action="store_true", help="Also download extra_questions.jsonl")
    args = parser.parse_args()

    questions = download_questions_jsonl(args.raw_dir)
    print(f"questions.jsonl -> {questions}")
    if args.extra:
        extra = download_extra_questions_jsonl(args.raw_dir)
        print(f"extra_questions.jsonl -> {extra}")


if __name__ == "__main__":
    main()
