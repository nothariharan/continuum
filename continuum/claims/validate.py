"""Contract v1 validation: claims and mentions must conform before touching HydraDB.

Validation is strict on purpose. A malformed claim is a poisoned graph edge;
rejecting it at the boundary is cheaper than debugging it in state resolution.

v1 semantics: timestamps are nullable when not stated (real ISO when present);
ids are stable 16-hex hashes or human `claim:`/`mention:` slugs; every claim
carries a non-empty evidence_span and an extraction_method.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .schema import (
    ARTIFACT_ID_RE,
    CLAIM_ID_RE,
    ISO_TS,
    MENTION_ID_RE,
    MENTION_TYPE_RE,
    PREDICATE_RE,
    SUPPORTED_MENTION_TYPES,
    SUPPORTED_PREDICATES,
    Claim,
    Mention,
)


class ContractError(ValueError):
    """A record violates the shared Artifact/Mention/Claim contract."""


def _require(record_id: str, field_name: str, value: Any, check: bool, why: str) -> None:
    if not check:
        raise ContractError(f"{record_id}: field '{field_name}' {why} (got {value!r})")


def _is_iso(value: str) -> bool:
    if ISO_TS.match(value) is None:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_claim(record: dict[str, Any]) -> Claim:
    claim_id = str(record.get("claim_id", ""))
    _require(claim_id, "claim_id", claim_id, CLAIM_ID_RE.match(claim_id) is not None, "must be a 16-hex hash or claim:<slug>")

    artifact_id = str(record.get("artifact_id", ""))
    _require(claim_id, "artifact_id", artifact_id, ARTIFACT_ID_RE.match(artifact_id) is not None, "must be dsid_<hex> or artifact:<key>")

    subject = record.get("subject_mention")
    predicate = record.get("predicate")
    object_ = record.get("object_mention")
    _require(claim_id, "subject_mention", subject, isinstance(subject, str) and subject.strip() != "", "must be non-empty mention text")
    _require(claim_id, "predicate", predicate, isinstance(predicate, str) and predicate in SUPPORTED_PREDICATES, f"must be one of {sorted(SUPPORTED_PREDICATES)}")
    _require(claim_id, "object_mention", object_, isinstance(object_, str) and object_.strip() != "", "must be non-empty mention text")

    observed = record.get("observed_at")
    valid_from = record.get("valid_from")
    valid_to = record.get("valid_to")
    for name, value in (("observed_at", observed), ("valid_from", valid_from), ("valid_to", valid_to)):
        _require(
            claim_id,
            name,
            value,
            value is None or (isinstance(value, str) and _is_iso(value)),
            "must be null or a real ISO date/datetime",
        )
    _require(
        claim_id,
        "valid_to",
        valid_to,
        valid_to is None or valid_from is None or str(valid_to)[:10] >= str(valid_from)[:10],
        "must not be earlier than valid_from",
    )

    confidence = record.get("confidence")
    _require(claim_id, "confidence", confidence, isinstance(confidence, (int, float)) and 0.0 <= float(confidence) <= 1.0, "must be a number in [0, 1]")

    method = record.get("extraction_method")
    _require(claim_id, "extraction_method", method, isinstance(method, str) and method.strip() != "", "must be non-empty (deterministic, llm, hybrid, hand-written)")

    evidence_span = record.get("evidence_span")
    _require(claim_id, "evidence_span", evidence_span, isinstance(evidence_span, str) and evidence_span.strip() != "", "must be a non-empty verbatim supporting quote")

    metadata = record.get("metadata")
    _require(claim_id, "metadata", metadata, metadata is None or isinstance(metadata, dict), "must be null or an object")

    return Claim(
        claim_id=claim_id,
        artifact_id=artifact_id,
        subject_mention=str(subject).strip(),
        predicate=str(predicate),
        object_mention=str(object_).strip(),
        observed_at=None if observed is None else str(observed),
        valid_from=None if valid_from is None else str(valid_from),
        valid_to=None if valid_to is None else str(valid_to),
        confidence=float(confidence),
        extraction_method=str(method).strip(),
        evidence_span=str(evidence_span).strip(),
        metadata=dict(metadata or {}),
    )


def validate_mention(record: dict[str, Any]) -> Mention:
    mention_id = str(record.get("mention_id", ""))
    _require(mention_id, "mention_id", mention_id, MENTION_ID_RE.match(mention_id) is not None, "must be a 16-hex hash or mention:<slug>")

    artifact_id = str(record.get("artifact_id", ""))
    _require(mention_id, "artifact_id", artifact_id, ARTIFACT_ID_RE.match(artifact_id) is not None, "must be dsid_<hex> or artifact:<key>")

    raw_text = record.get("raw_text", record.get("text"))
    _require(mention_id, "raw_text", raw_text, isinstance(raw_text, str) and raw_text.strip() != "", "must be non-empty mention text")

    mention_type = str(record.get("type", record.get("mention_type", "")))
    _require(mention_id, "type", mention_type, MENTION_TYPE_RE.match(mention_type) is not None and mention_type in SUPPORTED_MENTION_TYPES, f"must be one of {sorted(SUPPORTED_MENTION_TYPES)}")

    source = record.get("source", "")
    context = record.get("context", "")
    span_start = record.get("span_start")
    span_end = record.get("span_end")
    _require(mention_id, "source", source, isinstance(source, str) and source != "", "must be a non-empty source name")
    _require(mention_id, "context", context, isinstance(context, str), "must be a string")
    for span_name, span in (("span_start", span_start), ("span_end", span_end)):
        _require(mention_id, span_name, span, isinstance(span, int) and span >= 0, "must be non-negative int")
    _require(mention_id, "span_end", span_end, span_end > span_start, "must be greater than span_start")

    method = record.get("extraction_method")
    _require(mention_id, "extraction_method", method, isinstance(method, str) and method.strip() != "", "must be non-empty")
    confidence = record.get("confidence")
    _require(mention_id, "confidence", confidence, isinstance(confidence, (int, float)) and 0.0 <= float(confidence) <= 1.0, "must be a number in [0, 1]")

    return Mention(
        mention_id=mention_id,
        artifact_id=artifact_id,
        source=str(source),
        raw_text=str(raw_text).strip(),
        type=mention_type,
        context=str(context),
        source_identity=record.get("source_identity"),
        span_start=int(span_start),
        span_end=int(span_end),
        extraction_method=str(method).strip(),
        confidence=float(confidence),
    )
