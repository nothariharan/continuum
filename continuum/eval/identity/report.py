"""Coverage and distribution reporting for identity-pair gold dataset."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .schema import DATASET_VERSION, FEATURE_SLOTS, DEFAULT_DATASET_PATH

DEFAULT_REPORT_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "entity_resolution"
    / "v1"
    / "identity_pairs_report.json"
)
DEFAULT_INVENTORY = (
    Path(__file__).resolve().parents[3] / "data" / "extraction" / "mention_inventory.json"
)


def git_commit_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def inventory_hash(path: Path = DEFAULT_INVENTORY) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:12]


def build_identity_pairs_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    label_counts = Counter(row["label"] for row in rows)
    tag_counts = Counter(tag for row in rows for tag in row.get("difficulty_tags") or [])
    source_counts = Counter(row.get("candidate_source") or "unknown" for row in rows)

    coverage: dict[str, float] = {}
    stats: dict[str, dict[str, float | None]] = {}
    total = max(len(rows), 1)

    for slot in FEATURE_SLOTS:
        values = [
            row.get("features", {}).get(slot)
            for row in rows
            if isinstance(row.get("features"), dict) and row["features"].get(slot) is not None
        ]
        coverage[slot] = round(len(values) / total, 4)
        if values:
            stats[slot] = {
                "min": round(min(values), 4),
                "mean": round(mean(values), 4),
                "max": round(max(values), 4),
            }
        else:
            stats[slot] = {"min": None, "mean": None, "max": None}

    return {
        "dataset_version": DATASET_VERSION,
        "commit_sha": git_commit_sha(),
        "inventory_hash": inventory_hash(),
        "pair_count": len(rows),
        "label_distribution": dict(sorted(label_counts.items())),
        "difficulty_tag_histogram": dict(sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))),
        "candidate_source_breakdown": dict(sorted(source_counts.items())),
        "feature_coverage": coverage,
        "feature_stats": stats,
        "system_owner_next_step": (
            "Wire data/entity_resolution/v1/identity-pairs.jsonl into the resolver eval harness; "
            "tune REVIEW threshold on the UNCERTAIN tail using FeatureVector slots without changing "
            "continuum/entities/resolver.py."
        ),
    }


def write_identity_pairs_report(
    rows: list[dict[str, Any]],
    path: Path | None = None,
) -> Path:
    target = path or DEFAULT_REPORT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    report = build_identity_pairs_report(rows)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
