"""Phase 3 integration demo: resolver output -> resolutions -> claim load.

Consumes the tiny identity fixture, resolves mentions into canonical
entities, converts them to the resolutions format, and (with --load) loads
the known-good real claims against the RESOLVED lexicon instead of the
hand-written one. This is the first automated-resolution milestone:

    mention -> EntityCandidate -> resolver -> CanonicalEntity
        -> to_resolutions -> load_claims (unchanged HydraDB path)

Usage:
    python scripts/entity_resolution_demo.py [--load]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.entities import EntityResolver
from continuum.entities.bridge import to_resolutions
from continuum.entities.fixtures import load_candidates

ROOT = Path(__file__).resolve().parents[1]


def main(do_load: bool) -> None:
    resolver = EntityResolver()
    candidates = load_candidates()
    result = resolver.cluster(candidates)

    print("=== resolved entities (from fixture) ===")
    for key, entity in result["merged"].items():
        print(f"  {key:<32} mentions={sorted(entity.mentions)}")

    resolutions = to_resolutions(result["merged"].values())
    print(f"\n=== resolutions map ({len(resolutions)} entities) ===")
    print(json.dumps(resolutions, indent=2, ensure_ascii=False)[:1200])

    print(f"\n=== decision summary ===")
    print(f"  merged: {len(result['merged'])}  review: {len(result['review'])}  "
          f"separate: {len(result['separate'])}  abstained: {len(result['abstained'])}")

    if do_load:
        from continuum.claims import validate_claim
        from continuum.hydradb import HydraDBClient
        from continuum.hydradb.claims import load_claims

        claims = [
            validate_claim(json.loads(line))
            for line in (ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl")
            .open(encoding="utf-8")
            if line.strip()
        ]
        resolvable = {m for entry in resolutions.values() for m in entry["mentions"]}
        covered = [c for c in claims if c.subject_mention in resolvable and c.object_mention in resolvable]
        print(f"\n=== claim load against RESOLVED lexicon ===")
        print(f"  claims: {len(claims)}  fully covered by resolved lexicon: {len(covered)}")
        if not covered:
            print("  (resolved lexicon currently covers only the fixture entities; "
                  "run over the real mention inventory for coverage)")
            return
        with HydraDBClient() as client:
            load_result = load_claims(
                client,
                claims=covered,
                resolutions=resolutions,
                reset=True,
            )
        print(json.dumps(
            {k: v for k, v in load_result.__dict__.items() if k != "load_ms"}, indent=2
        ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--load", action="store_true", help="load real claims against resolved lexicon")
    args = parser.parse_args()
    main(do_load=args.load)
