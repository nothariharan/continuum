"""Pinned EnterpriseRAG-Bench v1.0.0 release manifest helpers."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST = Path(__file__).with_name("manifest_v1.0.0.json")

SOURCE_ALIASES = {
    "slack": "slack",
    "gmail": "gmail",
    "linear": "linear",
    "google_drive": "google_drive",
    "hubspot": "hubspot",
    "fireflies": "fireflies",
    "github": "github",
    "jira": "jira",
    "confluence": "confluence",
}


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def source_slices(source: str) -> list[dict]:
    source = SOURCE_ALIASES[source]
    prefix = f"{source}_slice_"
    return sorted(
        (a for a in load_manifest()["assets"] if a["name"].startswith(prefix)),
        key=lambda a: a["name"],
    )


def slice_files_per_source() -> dict[str, list[dict]]:
    return {source: source_slices(source) for source in SOURCE_ALIASES}


def asset_by_name(name: str) -> dict | None:
    for asset in load_manifest()["assets"]:
        if asset["name"] == name:
            return asset
    return None