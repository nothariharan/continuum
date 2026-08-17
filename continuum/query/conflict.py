"""Conflict resolution — ordering claims into state, not just listing them.

Turns a pile of contradictory claims into a decision:

  - all same subject                        -> definitive (consistent)
  - disjoint validity intervals, ordered    -> definitive succession
       current  = latest subject
       history  = earlier subjects
  - later observation supersedes earlier    -> definitive (superseded)
  - overlapping / contradictory, orderable  -> conflict (contradictory)
  - overlapping / contradictory, unordered  -> review (cannot establish)

The `review` status is the honest "I don't know because the evidence
conflicts" answer — never a guess.
"""

from __future__ import annotations

from typing import Any, Iterable

from continuum.hydradb import HydraDBClient

from .result import absent, result

OPEN_END = "9999-12-31"


def _sort_key(claim: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(claim.get("observed_at") or ""),
        str(claim.get("valid_from") or OPEN_END),
        str(claim.get("claim_id") or ""),
    )


def order_conflicts(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Claims sorted by observation time, then validity start, then id."""
    return sorted(claims, key=_sort_key)


def _interval(claim: dict[str, Any]) -> tuple[str, str]:
    return (
        str(claim.get("valid_from") or OPEN_END),
        str(claim.get("valid_to") or OPEN_END),
    )


def _intervals_disjoint(ordered: list[dict[str, Any]]) -> bool:
    """True when sorted-by-time intervals do not overlap (succession)."""
    for a, b in zip(ordered, ordered[1:]):
        a_end = _interval(a)[1]
        b_start = _interval(b)[0]
        if b_start < a_end:
            return False
    return True


def resolve_conflict_state(
    client: HydraDBClient,
    entity_key: str,
    predicate: str = "OWNS",
) -> dict[str, Any]:
    """Resolve contradictory claims about (entity, predicate) into state.

    Returns the canonical envelope with status one of:
      definitive  a single current value is established (history retained)
      conflict    contradictory claims that cannot be safely resolved
      review      claims conflict and their ordering is unknown
      absent      no claims at all
    """
    from .state import CONFLICTS

    rows = client.execute(
        CONFLICTS,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    if not rows:
        return absent(entity_key, predicate)

    subjects = sorted({row["subject_id"] for row in rows})
    if len(subjects) == 1:
        latest = max(rows, key=_sort_key)
        return result(
            entity_id=entity_key,
            predicate=predicate,
            status="definitive",
            value={"entity_id": latest["subject_id"], "name": latest["subject_name"]},
            valid_from=latest.get("valid_from"),
            valid_to=latest.get("valid_to"),
            confidence=0.9,
            claims=rows,
            history=order_conflicts(rows),
            resolution="consistent-single-subject",
        )

    ordered = order_conflicts(rows)
    if _intervals_disjoint(ordered):
        latest = ordered[-1]
        return result(
            entity_id=entity_key,
            predicate=predicate,
            status="definitive",
            value={"entity_id": latest["subject_id"], "name": latest["subject_name"]},
            valid_from=latest.get("valid_from"),
            valid_to=latest.get("valid_to"),
            confidence=0.9,
            conflicting_subjects=subjects,
            claims=rows,
            history=ordered,
            resolution="succession-disjoint-intervals",
        )

    observed = [c.get("observed_at") for c in ordered]
    strictly_ordered = all(observed) and len({o for o in observed if o}) == len(ordered)
    if strictly_ordered and len({c["subject_id"] for c in ordered}) > 1:
        latest = ordered[-1]
        return result(
            entity_id=entity_key,
            predicate=predicate,
            status="definitive",
            value={"entity_id": latest["subject_id"], "name": latest["subject_name"]},
            valid_from=latest.get("valid_from"),
            valid_to=latest.get("valid_to"),
            confidence=0.85,
            conflicting_subjects=subjects,
            claims=rows,
            history=ordered,
            resolution="superseded-by-later-observation",
        )

    if any(c.get("observed_at") or c.get("valid_from") for c in rows):
        return result(
            entity_id=entity_key,
            predicate=predicate,
            status="conflict",
            conflicting_subjects=subjects,
            claims=rows,
            history=ordered,
            resolution="contradictory-overlap",
        )

    return result(
        entity_id=entity_key,
        predicate=predicate,
        status="review",
        conflicting_subjects=subjects,
        claims=rows,
        history=ordered,
        resolution="cannot-establish-ordering",
    )


def conflicts_summary(payload: dict[str, Any]) -> str:
    """One-line human summary of a conflict-state payload (for traces/answers)."""
    status = payload.get("status", "absent")
    subjects = ", ".join(payload.get("conflicting_subjects") or [])
    value = (payload.get("value") or {}).get("name")
    if status == "definitive":
        return f"resolved: {value} (conflicting subjects: {subjects or 'none'})"
    if status == "conflict":
        return f"conflict: cannot resolve between {subjects}"
    if status == "review":
        return f"review: ordering unknown between {subjects}"
    return "no claims"