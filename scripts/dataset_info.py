"""Print the pinned Track 01 dataset manifest summary."""

from __future__ import annotations

import json

from continuum.dataset import load_manifest, slice_files_per_source

EXPECTED = {
    "slack": 275000,
    "gmail": 120000,
    "linear": 35000,
    "google_drive": 25000,
    "hubspot": 15000,
    "fireflies": 10000,
    "github": 8000,
    "jira": 6000,
    "confluence": 5000,
}


def main() -> int:
    manifest = load_manifest()
    print(f"Dataset:      {manifest['dataset']}")
    print(f"Release:      {manifest['release']}")
    print(f"Source:       {manifest['source']}")
    print(f"HuggingFace:  {manifest['huggingface']}")
    print(f"License:      {manifest['license']}")
    print(f"Paper:        {manifest['paper']}")
    print(f"Published:    {manifest['published_at']}")
    print(f"Release assets: {manifest['asset_count']}")
    print()
    print(f"{'source':<14} {'slices':>6} {'bytes':>12}  expected docs")
    total_bytes = 0
    slices = 0
    for source, assets in slice_files_per_source().items():
        n = len(assets)
        size = sum(a["size"] for a in assets)
        total_bytes += size
        slices += n
        expected = EXPECTED.get(source, "?")
        print(f"{source:<14} {n:>6} {size:>12,}  {expected:,}")
    print(f"{'TOTAL':<14} {slices:>6} {total_bytes:>12,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())