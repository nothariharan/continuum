"""Load the Phase 2B claim fixture into real HydraDB.

Pipeline: claims.jsonl -> contract validation -> manual resolution map ->
HydraDB (entity nodes, Claim nodes, SOURCED_FROM/ABOUT/predicate/CONTRADICTS)
-> read back verification.

Usage:
    python scripts/load_phase2b_claims.py [--reset] [--claims FILE] [--resolutions FILE]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.claims import load_claims
from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import load_claims as load_claims_graph

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "phase2b"

SOURCES = [
    {"key": "source:slack", "name": "Slack"},
    {"key": "source:gmail", "name": "Gmail"},
    {"key": "source:linear", "name": "Linear"},
    {"key": "source:confluence", "name": "Confluence"},
    {"key": "source:fireflies", "name": "Fireflies"},
    {"key": "source:github", "name": "GitHub"},
    {"key": "source:jira", "name": "Jira"},
    {"key": "source:google_drive", "name": "Google Drive"},
    {"key": "source:hubspot", "name": "HubSpot"},
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(reset: bool = False, claims_path: Path | None = None, resolutions_path: Path | None = None) -> dict:
    claims_file = claims_path or FIXTURE / "claims.jsonl"
    resolutions_file = resolutions_path or FIXTURE / "resolutions.json"
    artifacts_file = FIXTURE / "artifacts.jsonl"

    claims = load_claims(claims_file)
    resolutions = read_json(resolutions_file)
    fixture_artifacts = []
    if artifacts_file.exists():
        for line in artifacts_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                fixture_artifacts.append(json.loads(line))

    with HydraDBClient() as client:
        result = load_claims_graph(
            client,
            claims=claims,
            resolutions=resolutions,
            fixture_artifacts=fixture_artifacts,
            fixture_sources=SOURCES,
            reset=reset,
        )
    return {
        "claims": len(claims),
        "artifacts": result.artifacts,
        "sources": result.sources,
        "entities": result.entities,
        "relationships": result.relationships,
        "load_ms": round(result.load_ms, 2),
        "read_back_ms": round(result.read_back_ms, 2),
        "read_back_count": result.read_back_count,
        "mismatches": result.mismatches,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    print("Phase 2B claims loaded")
    print(json.dumps(main(reset=args.reset), indent=2))
