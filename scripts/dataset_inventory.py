"""Write the Phase 2A dataset inventory to data/metadata/dataset_inventory.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.dataset.download import download_all_documents, open_corpus
from continuum.dataset.inventory import inventory_corpus, inventory_to_dict

DEFAULT_RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "metadata" / "dataset_inventory.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory the pinned Track 01 corpus")
    parser.add_argument("--cache", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    download_all_documents(args.cache, verify=True)
    with open_corpus(args.cache) as archive:
        inventory = inventory_corpus(archive)
    payload = inventory_to_dict(inventory)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())