"""Contract validation: claims and mentions must conform before touching HydraDB.

Validation is strict on purpose. A malformed claim is a poisoned graph edge;
rejecting it at the boundary is cheaper than debugging it in state resolution.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from typing import Any

from .schema import (
    ARTIFACT_ID_RE,
    CLAIM_ID_RE,
    ISO_TS,
    MENTION_ID_RE,
    MENTION_TYPE_RE,
    PREDICATE_RE,
    VALID_MENTION_TYPES,
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
    _require(claim_id, "claim_id", claim_id, CLAIM_ID_RE.match(claim_id) is not None, "must match claim:<slug>")

    artifact_id = str(record.get("artifact_id", ""))
    _require(claim_id, "artifact_id", artifact_id, ARTIFACT_ID_RE.match(artifact_id) is not None, "must be dsid_<hex> or artifact:<key>")

    subject = record.get("subject_mention")
    predicate = record.get("predicate")
    object_ = record.get("object_mention")
    _require(claim_id, "subject_mention", subject, isinstance(subject, str) and subject.strip() != "", "must be non-empty mention text")
    _require(claim_id, "predicate", predicate, isinstance(predicate, str) and PREDICATE_RE.match(predicate) is not None, "must match [A-Z][A-Z_]+")
    _require(claim_id, "object_mention", object_, isinstance(object_, str) and object_.strip() != "", "must be non-empty mention text")

    observed = str(record.get("observed_at", ""))
    valid_from = str(record.get("valid_from", ""))
    valid_to = record.get("valid_to")
    _require(claim_id, "observed_at", observed, _is_iso(observed), "must be a real ISO date/datetime")
    _require(claim_id, "valid_from", valid_from, _is_iso(valid_from), "must be a real ISO date/datetime")
    _require(
        claim_id,
        "valid_to",
        valid_to,
        valid_to is None or (isinstance(valid_to, str) and _is_iso(valid_to)),
        "must be null or a real ISO date/datetime",
    )
    _require(
        claim_id,
        "valid_to",
        valid_to,
        valid_to is None or str(valid_to)[:10] >= valid_from[:10],
        "must not be earlier than valid_from",
    )

    confidence = record.get("confidence")
    _require(claim_id, "confidence", confidence, isinstance(confidence, (int, float)) and 0.0 <= float(confidence) <= 1.0, "must be a number in [0, 1]")

    method = record.get("extraction_method")
    _require(claim_id, "extraction_method", method, isinstance(method, str) and method.strip() != "", "must be non-empty (e.g. hand-written, llm-extraction)")

    return Claim(
        claim_id=claim_id,
        artifact_id=artifact_id,
        subject_mention=str(subject).strip(),
        predicate=str(predicate),
        object_mention=str(object_).strip(),
        observed_at=observed,
        valid_from=valid_from,
        valid_to=None if valid_to is None else str(valid_to),
        confidence=float(confidence),
        extraction_method=str(method).strip(),
    )


def validate_mention(record: dict[str, Any]) -> Mention:
    mention_id = str(record.get("mention_id", ""))
    _require(mention_id, "mention_id", mention_id, MENTION_ID_RE.match(mention_id) is not None, "must match mention:<slug>")

    artifact_id = str(record.get("artifact_id", ""))
    _require(mention_id, "artifact_id", artifact_id, ARTIFACT_ID_RE.match(artifact_id) is not None, "must be dsid_<hex> or artifact:<key>")

    text = record.get("text")
    _require(mention_id, "text", text, isinstance(text, str) and text.strip() != "", "must be non-empty mention text")

    mention_type = str(record.get("mention_type", ""))
    _require(mention_id, "mention_type", mention_type, MENTION_TYPE_RE.match(mention_type) is not None and mention_type in VALID_MENTION_TYPES, f"must be one of {sorted(VALID_MENTION_TYPES)}")

    span_start = record.get("span_start")
    span_end = record.get("span_end")
    for span_name, span in (("span_start", span_start), ("span_end", span_end)):
        _require(mention_id, span_name, span, span is None or (isinstance(span, int) and span >= 0), "must be null or non-negative int")
    if span_start is not None and span_end is not None:
        _require(mention_id, "span_end", span_end, span_end > span_start, "must be greater than span_start")

    return Mention(
        mention_id=mention_id,
        artifact_id=artifact_id,
        text=str(text).strip(),
        mention_type=mention_type,
        span_start=span_start,
        span_end=span_end,
    )
