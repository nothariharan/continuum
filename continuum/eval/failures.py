"""Classify extraction evaluation failures for the failure corpus."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from continuum.claims.schema import SUPPORTED_PREDICATES
from continuum.eval.gold_v1 import GoldBenchmark, GoldClaimRow
from continuum.eval.metrics import _claim_key, gold_claim_key
from continuum.extract.schemas import Claim

FAILURE_CATEGORIES = (
    "INVALID_SUBJECT",
    "INVALID_OBJECT",
    "WRONG_PREDICATE",
    "MISSING_TIMESTAMP",
    "BAD_TIMESTAMP",
    "UNSUPPORTED_ENTITY_PAIR",
    "WEAK_EVIDENCE",
    "AMBIGUOUS_ROLE",
    "MULTI_ENTITY",
    "NO_RELATIONSHIP",
    "FALSE_POSITIVE_ABSTENTION",
    "MISSING_CLAIM",
)

GENERIC_OBJECT_WORDS = frozenset(
    {
        "model",
        "tokens",
        "batching",
        "place",
        "treaty",
        "finance",
        "incidents",
        "deployment",
        "runtime",
        "customer",
        "control",
        "sequence",
        "hit",
        "infra",
        "vendor",
        "rollout",
        "your",
        "allocator",
        "embedding",
        "contract",
    }
)


def _is_iso(value: str | None) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def classify_prediction_vs_gold(
    claim: Claim,
    *,
    artifact_content: str,
    artifact_timestamp: str | None,
    gold_expectation: str,
    gold_rows: list[GoldClaimRow],
) -> str | None:
    """Return a failure category if this prediction is a failure, else None."""
    pred_key = _claim_key(claim.subject_mention, claim.predicate, claim.object_mention)
    valid_gold = {gold_claim_key(row) for row in gold_rows if row.status == "VALID"}

    if gold_expectation == "NO_CLAIM":
        return "FALSE_POSITIVE_ABSTENTION"

    if gold_expectation == "AMBIGUOUS":
        return "AMBIGUOUS_ROLE"

    if pred_key in valid_gold:
        return None

    if claim.predicate not in SUPPORTED_PREDICATES:
        return "WRONG_PREDICATE"

    subject = claim.subject_mention.strip()
    obj = claim.object_mention.strip()
    if not subject or len(subject.split()) > 8:
        return "INVALID_SUBJECT"
    if not obj or obj.lower() in GENERIC_OBJECT_WORDS or len(obj.split()) > 6:
        return "INVALID_OBJECT"

    if not claim.observed_at and not artifact_timestamp:
        return "MISSING_TIMESTAMP"
    for field in (claim.observed_at, claim.valid_from, claim.valid_to):
        if field is not None and not _is_iso(field):
            return "BAD_TIMESTAMP"

    evidence = (claim.evidence_span or "").strip()
    if not evidence or evidence.lower() not in artifact_content.lower():
        return "WEAK_EVIDENCE"

    if valid_gold and all(row.predicate != claim.predicate for row in gold_rows if row.status == "VALID"):
        return "WRONG_PREDICATE"

    if claim.predicate in {"DEPENDS_ON", "BLOCKS"} and obj.lower() in GENERIC_OBJECT_WORDS:
        return "UNSUPPORTED_ENTITY_PAIR"

    return "WRONG_PREDICATE"


def classify_missing_gold_claims(
    *,
    artifact_id: str,
    gold_rows: list[GoldClaimRow],
    predicted: list[Claim],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    pred_keys = {_claim_key(c.subject_mention, c.predicate, c.object_mention) for c in predicted}
    for row in gold_rows:
        if row.status != "VALID":
            continue
        key = gold_claim_key(row)
        if key not in pred_keys:
            failures.append(
                {
                    "category": "MISSING_CLAIM",
                    "artifact_id": artifact_id,
                    "gold": row.to_dict(),
                    "reason": "valid gold claim not extracted",
                }
            )
    return failures


def build_failure_corpus(
    predicted: list[Claim],
    benchmark: GoldBenchmark,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    content_by_id = {row["id"]: row.get("content", "") for row in benchmark.artifacts}
    timestamp_by_id = {row["id"]: row.get("timestamp") for row in benchmark.artifacts}
    summary: dict[str, int] = {cat: 0 for cat in FAILURE_CATEGORIES}
    examples: list[dict[str, Any]] = []

    claims_by_artifact: dict[str, list[GoldClaimRow]] = {}
    for row in benchmark.claims:
        claims_by_artifact.setdefault(row.artifact_id, []).append(row)

    for artifact_id in sorted(benchmark.artifact_ids):
        expectation = benchmark.artifact_claim_expectation(artifact_id)
        gold_rows = claims_by_artifact.get(artifact_id, [])
        preds = [c for c in predicted if c.artifact_id == artifact_id]

        for failure in classify_missing_gold_claims(
            artifact_id=artifact_id,
            gold_rows=gold_rows,
            predicted=preds,
        ):
            summary[failure["category"]] += 1
            examples.append(failure)

        for claim in preds:
            category = classify_prediction_vs_gold(
                claim,
                artifact_content=content_by_id.get(artifact_id, ""),
                artifact_timestamp=timestamp_by_id.get(artifact_id),
                gold_expectation=expectation,
                gold_rows=gold_rows,
            )
            if category is None:
                continue
            summary[category] += 1
            examples.append(
                {
                    "category": category,
                    "artifact_id": artifact_id,
                    "prediction": {
                        "subject_mention": claim.subject_mention,
                        "predicate": claim.predicate,
                        "object_mention": claim.object_mention,
                        "evidence_span": claim.evidence_span,
                        "extraction_method": claim.extraction_method,
                        "confidence": claim.confidence,
                    },
                    "gold_expectation": expectation,
                }
            )

    summary = {k: v for k, v in summary.items() if v}
    return summary, examples
