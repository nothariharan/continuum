"""Contract v1 validation for Phase 2B extraction outputs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from continuum.extract.schemas import (
    EXTRACTION_METHODS,
    MENTION_TYPES,
    SUPPORTED_PREDICATES,
    claim_from_dict,
    load_artifacts_jsonl,
    mention_from_dict,
    read_jsonl,
)

DSID_PATTERN = re.compile(r"^dsid_[0-9a-f]{32}$")


def _stable_hash(*parts: str) -> str:
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class ValidationReport:
    sample_artifact_count: int
    mention_rows: int
    claim_rows: int
    artifacts_with_mentions: int
    artifacts_with_claims: int
    artifacts_with_any_extraction: int
    artifacts_with_zero_extractions: int
    orphan_artifact_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "sample_artifact_count": self.sample_artifact_count,
            "mention_rows": self.mention_rows,
            "claim_rows": self.claim_rows,
            "artifacts_with_mentions": self.artifacts_with_mentions,
            "artifacts_with_claims": self.artifacts_with_claims,
            "artifacts_with_any_extraction": self.artifacts_with_any_extraction,
            "artifacts_with_zero_extractions": self.artifacts_with_zero_extractions,
            "orphan_artifact_ids": self.orphan_artifact_ids,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[:50],
            "warnings": self.warnings[:50],
        }


def validate_extraction_outputs(
    *,
    sample_path: Path,
    mentions_path: Path,
    claims_path: Path,
    check_spans: bool = False,
) -> ValidationReport:
    sample_rows = load_artifacts_jsonl(sample_path)
    sample_ids = {row["id"] for row in sample_rows}
    content_by_id = {row["id"]: row.get("content", "") for row in sample_rows}

    seen_mention_ids: set[str] = set()
    seen_claim_ids: set[str] = set()
    mention_artifact_ids: set[str] = set()
    claim_artifact_ids: set[str] = set()
    mention_row_count = 0
    claim_row_count = 0
    errors: list[str] = []
    warnings: list[str] = []

    for line_no, row in enumerate(read_jsonl(mentions_path), start=1):
        mention_row_count += 1
        try:
            mention = mention_from_dict(row)
        except (TypeError, ValueError) as exc:
            errors.append(f"mentions.jsonl:{line_no}: invalid row: {exc}")
            continue

        if mention.artifact_id not in sample_ids:
            errors.append(f"mentions.jsonl:{line_no}: orphan artifact_id {mention.artifact_id}")
        mention_artifact_ids.add(mention.artifact_id)

        if not DSID_PATTERN.match(mention.artifact_id):
            errors.append(f"mentions.jsonl:{line_no}: bad artifact_id format {mention.artifact_id}")

        if mention.type not in MENTION_TYPES:
            errors.append(f"mentions.jsonl:{line_no}: unsupported mention type {mention.type}")

        if mention.extraction_method not in EXTRACTION_METHODS:
            errors.append(
                f"mentions.jsonl:{line_no}: bad extraction_method {mention.extraction_method}"
            )

        if not (0.0 <= mention.confidence <= 1.0):
            errors.append(f"mentions.jsonl:{line_no}: confidence out of range {mention.confidence}")

        expected_id = _stable_hash(
            mention.artifact_id, mention.raw_text, mention.type, str(mention.span_start)
        )
        if mention.mention_id != expected_id:
            errors.append(f"mentions.jsonl:{line_no}: mention_id mismatch for {mention.raw_text!r}")

        if mention.span_start < 0 or mention.span_end < mention.span_start:
            errors.append(f"mentions.jsonl:{line_no}: invalid span [{mention.span_start}, {mention.span_end})")

        if check_spans:
            content = content_by_id.get(mention.artifact_id, "")
            if content and mention.span_end <= len(content):
                slice_text = content[mention.span_start : mention.span_end]
                if mention.raw_text not in slice_text and slice_text not in mention.raw_text:
                    warnings.append(
                        f"mentions.jsonl:{line_no}: span text mismatch for {mention.raw_text!r}"
                    )

        if mention.mention_id in seen_mention_ids:
            errors.append(f"mentions.jsonl:{line_no}: duplicate mention_id {mention.mention_id}")
        seen_mention_ids.add(mention.mention_id)

    for line_no, row in enumerate(read_jsonl(claims_path), start=1):
        claim_row_count += 1
        try:
            claim = claim_from_dict(row)
        except (TypeError, ValueError) as exc:
            errors.append(f"claims.jsonl:{line_no}: invalid row: {exc}")
            continue

        if claim.artifact_id not in sample_ids:
            errors.append(f"claims.jsonl:{line_no}: orphan artifact_id {claim.artifact_id}")
        claim_artifact_ids.add(claim.artifact_id)

        if not DSID_PATTERN.match(claim.artifact_id):
            errors.append(f"claims.jsonl:{line_no}: bad artifact_id format {claim.artifact_id}")

        if claim.predicate not in SUPPORTED_PREDICATES:
            errors.append(f"claims.jsonl:{line_no}: unsupported predicate {claim.predicate}")

        if claim.extraction_method not in EXTRACTION_METHODS:
            errors.append(f"claims.jsonl:{line_no}: bad extraction_method {claim.extraction_method}")

        if not (0.0 <= claim.confidence <= 1.0):
            errors.append(f"claims.jsonl:{line_no}: confidence out of range {claim.confidence}")

        if not claim.evidence_span.strip():
            errors.append(f"claims.jsonl:{line_no}: empty evidence_span")

        expected_id = _stable_hash(
            claim.artifact_id, claim.subject_mention, claim.predicate, claim.object_mention
        )
        if claim.claim_id != expected_id:
            errors.append(
                f"claims.jsonl:{line_no}: claim_id mismatch for {claim.predicate} "
                f"{claim.subject_mention!r} -> {claim.object_mention!r}"
            )

        if claim.claim_id in seen_claim_ids:
            errors.append(f"claims.jsonl:{line_no}: duplicate claim_id {claim.claim_id}")
        seen_claim_ids.add(claim.claim_id)

    orphan = sorted((mention_artifact_ids | claim_artifact_ids) - sample_ids)
    any_extraction = mention_artifact_ids | claim_artifact_ids
    zero_extraction = len(sample_ids - any_extraction)

    if zero_extraction:
        warnings.append(
            f"{zero_extraction} sample artifacts have zero mentions and zero claims "
            "(expected for sparse sources like google_drive/confluence)"
        )

    return ValidationReport(
        sample_artifact_count=len(sample_ids),
        mention_rows=mention_row_count,
        claim_rows=claim_row_count,
        artifacts_with_mentions=len(mention_artifact_ids),
        artifacts_with_claims=len(claim_artifact_ids),
        artifacts_with_any_extraction=len(any_extraction),
        artifacts_with_zero_extractions=zero_extraction,
        orphan_artifact_ids=orphan,
        errors=errors,
        warnings=warnings,
    )
