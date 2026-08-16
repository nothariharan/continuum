"""V2 pipeline: artifact -> candidates -> deterministic relations -> claims.

Keeps the stages separate so the report can attribute failures:
    candidate coverage -> pair coverage -> relation quality -> graph-loadable.
"""

from __future__ import annotations

import json
from typing import Any

from continuum.dataset.artifact import Artifact

from .candidates import find_candidates
from .relations import extract_relations


def run_pipeline(
    artifacts: list[Artifact],
    resolutions: dict[str, dict],
) -> dict[str, Any]:
    """Run the deterministic v2 pipeline over artifacts.

    Returns per-artifact detail plus aggregate coverage counts:
      artifacts, with_candidates, with_pair, claims, claims_by_predicate
    """
    detail = []
    claims: list[dict[str, Any]] = []
    for artifact in artifacts:
        candidates = find_candidates(artifact, resolutions)
        rels = extract_relations(artifact, candidates, resolutions) if len(candidates) >= 2 else []
        person_keys = sorted({c.entity_key for c in candidates if c.label == "Person"})
        account_keys = sorted({c.entity_key for c in candidates if c.label == "Account"})
        detail.append(
            {
                "artifact_id": artifact.id,
                "source": artifact.source,
                "title": (artifact.title or "")[:80],
                "candidates": [c.entity_key for c in candidates],
                "person_keys": person_keys,
                "account_keys": account_keys,
                "pair": bool(person_keys and account_keys),
                "relations": rels,
            }
        )
        claims.extend(rels)
    return {
        "artifacts": len(artifacts),
        "with_candidates": sum(1 for d in detail if d["candidates"]),
        "with_pair": sum(1 for d in detail if d["pair"]),
        "claims": len(claims),
        "claims_by_predicate": _count_by_predicate(claims),
        "detail": detail,
    }


def _count_by_predicate(claims: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for claim in claims:
        counts[claim["predicate"]] = counts.get(claim["predicate"], 0) + 1
    return counts


def write_claims_jsonl(claims: list[dict[str, Any]], path) -> int:
    with path.open("w", encoding="utf-8") as handle:
        for claim in claims:
            handle.write(json.dumps(claim, ensure_ascii=False) + "\n")
    return len(claims)
