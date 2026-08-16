#!/usr/bin/env python3
"""Verify full EnterpriseRAG-Bench corpus and question set before baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from continuum.dataset.download import all_documents_path, benchmark_cache_dir, download_all_documents
from continuum.dataset.inventory import inventory_corpus
from continuum.dataset.manifest import load_manifest as load_dataset_manifest
from continuum.eval.benchmark.questions import load_official_questions
from continuum.eval.benchmark.schema import DEFAULT_BENCHMARK_ROOT, git_commit_sha, write_json

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "data" / "metadata" / "dataset_inventory.json"
OUT_INVENTORY = ROOT / "data" / "metadata" / "benchmark_full_inventory.json"
OUT_QUESTIONS = DEFAULT_BENCHMARK_ROOT / "full-v1" / "full-v1-question-manifest.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    cache_dir = ROOT / "data" / "raw"
    cache = benchmark_cache_dir(cache_dir)
    manifest = load_dataset_manifest()
    asset = next(a for a in manifest["assets"] if a["name"] == "all_documents.zip")

    if not args.skip_download:
        download_all_documents(cache, verify=True)

    zip_path = all_documents_path(cache)
    if not zip_path.exists():
        raise SystemExit(f"missing corpus: {zip_path}")

    actual_sha = _sha256_file(zip_path)
    if actual_sha != asset["sha256"]:
        raise SystemExit(f"checksum mismatch: expected {asset['sha256']} got {actual_sha}")

    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        inv = inventory_corpus(archive, scan_cap=600)

    questions = load_official_questions()
    qids = [str(q["question_id"]) for q in questions]
    if len(questions) != 500:
        raise SystemExit(f"expected 500 questions, got {len(questions)}")
    if len(set(qids)) != 500:
        raise SystemExit("duplicate question IDs detected")

    if INVENTORY_PATH.exists():
        expected = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        if int(expected.get("total_files", 0)) != inv.total_files:
            raise SystemExit(
                f"document count mismatch: inventory={expected.get('total_files')} live={inv.total_files}"
            )

    inventory_report = {
        "dataset_release": manifest.get("release", "v1.0.0"),
        "archive_path": str(zip_path),
        "archive_sha256": actual_sha,
        "document_count": inv.total_files,
        "total_bytes": inv.total_bytes,
        "source_counts": {s.source: s.file_count for s in inv.sources},
        "extraction_timestamp": datetime.now(UTC).isoformat(),
        "commit_sha": git_commit_sha(),
    }
    write_json(OUT_INVENTORY, inventory_report)

    question_manifest = {
        "question_count": len(questions),
        "unique_ids": len(set(qids)),
        "category_counts": dict(Counter(q.get("question_type", "unknown") for q in questions)),
        "questions_sha256": hashlib.sha256(
            "".join(json.dumps(q, sort_keys=True) for q in questions).encode()
        ).hexdigest(),
        "commit_sha": git_commit_sha(),
    }
    write_json(OUT_QUESTIONS, question_manifest)

    print(json.dumps({"inventory": inventory_report, "questions": question_manifest}, indent=2))


if __name__ == "__main__":
    main()
