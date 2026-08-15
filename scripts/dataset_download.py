"""Download and verify the pinned EnterpriseRAG-Bench v1.0.0 corpus (checksum-verified)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.dataset.download import download_all_documents
from continuum.dataset.manifest import load_manifest

DEFAULT_RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the pinned Track 01 dataset")
    parser.add_argument("--cache", type=Path, default=DEFAULT_RAW, help="cache dir (gitignored)")
    parser.add_argument("--skip-verify", action="store_true", help="skip checksum verification")
    args = parser.parse_args()

    manifest = load_manifest()
    zip_path = download_all_documents(args.cache, verify=not args.skip_verify)
    print(f"archive:  {zip_path}")
    print(f"size:     {zip_path.stat().st_size:,} bytes")
    print(f"release:  {manifest['release']} (MIT, {manifest['paper']})")

    report = args.cache / "download_report.json"
    report.write_text(
        json.dumps(
            {"release": manifest["release"], "archive": str(zip_path), "bytes": zip_path.stat().st_size},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())