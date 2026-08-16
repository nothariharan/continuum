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


def _allowed_predicates(subject_label: str, object_label: str, candidate: str) -> set[str]:
    """Deterministic allowed set for refinement — never offers predicates the
    pair cannot support, and never REVIEWS/BLOCKS/DEPENDS_ON for thread
    refinement (they would bias the model away from the ownership family)."""
    person_to_business = {"OWNS", "MAINTAINS", "LEADS", "ASSIGNED_TO"}
    if subject_label == "Person" and object_label in {"Account", "Project", "Team"}:
        return person_to_business
    if subject_label == "Person" and object_label == "Service":
        return {"OWNS", "MAINTAINS", "LEADS"}
    if subject_label in {"Project", "Service"} and object_label in {"Project", "Service"}:
        return {"BLOCKS", "DEPENDS_ON"}
    return {candidate}


def _context_window(artifact_content: str, needle: str, radius: int = 450) -> str:
    """Verbatim window around the subject mention — deterministic, no invention."""
    content = artifact_content or ""
    if "\\n" in content:
        content = content.replace("\\n", "\n")
    idx = content.lower().find(needle.lower())
    if idx < 0:
        return content[: radius * 2]
    start = max(0, idx - radius)
    end = min(len(content), idx + len(needle) + radius)
    return content[start:end]


def _email_headers(artifact_content: str) -> str:
    """Scan the WHOLE artifact for email header lines (threads have multiple
    From/To/Subject blocks beyond the first 30 lines)."""
    content = artifact_content or ""
    if "\\n" in content:
        content = content.replace("\\n", "\n")
    found = []
    for line in content.splitlines():
        lower = line.strip().lower()
        if lower.startswith(("from:", "to:", "cc:", "subject:", "date:")):
            found.append(line.strip())
    return "\n".join(found[:12])


def refine_ambiguous_claims(
    claims: list[dict[str, Any]],
    provider,
    resolutions: dict[str, dict],
    *,
    mode: str = "ambiguous",
    artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply a PredicateRefinementProvider to claims.

    mode="ambiguous": only claims whose metadata marks them ambiguous
    (email-thread, thread-ae-label, slack-csm). mode="all": every claim.

    Never invents entities/evidence/timestamps — only the predicate is
    rewritten (and the claim_id re-derived with the new predicate).
    Returns {claims, refined, abstained, calls, latency_ms, per_claim}.
    """
    from .refinement import ABSTAIN

    refined_count = 0
    abstained: list[dict[str, Any]] = []
    calls = 0
    latency = 0.0
    per_claim = []
    out: list[dict[str, Any]] = []

    for claim in claims:
        metadata = claim.get("metadata") or {}
        ambiguous = bool(metadata.get("ambiguous")) or mode == "all"
        candidate = claim["predicate"]
        if not ambiguous:
            out.append(claim)
            continue

        subject_label = metadata.get("subject_label") or "person"
        object_label = metadata.get("object_label") or "account"
        allowed = _allowed_predicates(subject_label, object_label, candidate)
        context = {
            "subject": claim["subject_mention"],
            "subject_type": subject_label,
            "object": claim["object_mention"],
            "object_type": object_label,
            "candidate_predicate": candidate,
            "allowed_predicates": sorted(allowed),
            "evidence": claim.get("evidence_span", ""),
        }
        artifact = (artifacts or {}).get(claim["artifact_id"])
        if artifact is not None:
            content = getattr(artifact, "content", "") or ""
            if "\\n" in content:
                content = content.replace("\\n", "\n")
            context["artifact"] = content
            headers = _email_headers(content)
            if headers:
                context["headers"] = headers
        calls += 1
        result = provider.refine(context)
        latency += result.latency_ms

        final = claim
        if result.abstained:
            abstained.append(claim)
        elif result.predicate != candidate:
            refined_count += 1
            final = {**claim, "predicate": result.predicate}
            final["claim_id"] = _rehash_claim(final, resolutions)
            final["metadata"] = {**metadata,
                                 "refined": True,
                                 "refined_from": candidate,
                                 "refinement_confidence": result.confidence,
                                 "refinement_reason": result.reason[:200],
                                 "refinement_provider": result.provider}
        per_claim.append({
            "claim_id": claim["claim_id"],
            "artifact_id": claim["artifact_id"],
            "subject": claim["subject_mention"],
            "object": claim["object_mention"],
            "candidate_predicate": candidate,
            "final_predicate": final["predicate"],
            "confidence": result.confidence,
            "latency_ms": round(result.latency_ms, 1),
            "abstained": result.abstained,
            "refined": final.get("metadata", {}).get("refined", False),
        })
        out.append(final)

    return {
        "claims": out,
        "refined": refined_count,
        "abstained": len(abstained),
        "calls": calls,
        "latency_ms": round(latency, 1),
        "per_claim": per_claim,
    }


def _rehash_claim(claim: dict[str, Any], resolutions: dict[str, dict]) -> str:
    from continuum.claims.schema import stable_hash

    return stable_hash(
        claim["artifact_id"], claim["subject_mention"], claim["predicate"], claim["object_mention"]
    )


def write_claims_jsonl(claims: list[dict[str, Any]], path) -> int:
    with path.open("w", encoding="utf-8") as handle:
        for claim in claims:
            handle.write(json.dumps(claim, ensure_ascii=False) + "\n")
    return len(claims)
