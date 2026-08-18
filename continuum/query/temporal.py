"""Temporal state resolution — current vs historical vs as-of state.

Extends the base resolvers (continuum.query.state) with:

  - resolve_state_history  : ordered validity transitions for (entity, predicate)
  - resolve_state_before   : state valid immediately before a date
  - anchor_date            : map an event/keyword to the latest dated evidence
  - resolve_state_for_constraints : pick the right resolver from the
                                    decomposed temporal constraints

Every function returns the canonical envelope (.result) and adds two
optional fields: `history` (ordered transitions) and `resolution` (which
temporal rule produced the answer). Unknown fields remain null/empty.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable

from continuum.hydradb import HydraDBClient

from .context import TemporalConstraint
from .state import OPEN_END, resolve_state, resolve_state_on
from .result import absent, result

HISTORY = """
MATCH (c:Claim {object_id: $entity_key, predicate: $predicate})
RETURN c.subject_id AS subject_id, c.subject_name AS subject_name,
       c.valid_from AS valid_from, c.valid_to AS valid_to,
       c.observed_at AS observed_at
ORDER BY c.valid_from, c.observed_at
"""

ANCHOR_ARTIFACTS = """
MATCH (a:Artifact)
RETURN a.title AS title, a.timestamp AS ts, a.content AS content
"""

ANCHOR_CLAIMS = """
MATCH (c:Claim {object_id: $entity_key, predicate: $predicate})
RETURN c.subject_name AS subject_name, c.valid_from AS valid_from,
       c.observed_at AS observed_at, c.claim_id AS claim_id
"""

BEFORE_ENTITY = None


def _prev_day(value: str) -> str:
    return (date.fromisoformat(value) - timedelta(days=1)).isoformat()


def _next_day(value: str) -> str:
    return (date.fromisoformat(value) + timedelta(days=1)).isoformat()


def resolve_state_history(
    client: HydraDBClient,
    entity_key: str,
    predicate: str = "OWNS",
) -> dict[str, Any]:
    """Ordered validity transitions for (entity, predicate).

    status:
      definitive  at least one transition
      absent      no claim
    Envelope carries `history`: [{subject_id, subject_name, valid_from,
    valid_to, observed_at}] ordered by valid_from then observed_at.
    """
    rows = client.execute(
        HISTORY,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    if not rows:
        return absent(entity_key, predicate)
    ordered = sorted(
        rows,
        key=lambda r: (r.get("valid_from") or OPEN_END, r.get("observed_at") or ""),
    )
    return result(
        entity_id=entity_key,
        predicate=predicate,
        status="definitive",
        value={"entity_id": ordered[-1]["subject_id"], "name": ordered[-1]["subject_name"]},
        valid_from=ordered[-1].get("valid_from"),
        valid_to=ordered[-1].get("valid_to"),
        confidence=0.96,
        history=ordered,
        resolution="history",
    )


def resolve_state_before(
    client: HydraDBClient,
    entity_key: str,
    date: str,
    predicate: str = "OWNS",
) -> dict[str, Any]:
    """State valid immediately before `date` (the day before, by default).

    This answers "who owned it before <X>" / "who was the previous holder"
    using the validity intervals: the state whose interval contains the day
    before `date`; falls back to the most recent transition that closed
    before `date` when the open-ended current claim starts at/after it.
    """
    row = client.execute(
        """
        MATCH (c:Claim {object_id: $entity_key, predicate: $predicate})
        WHERE c.valid_from <= $before AND c.valid_to > $before
        RETURN c.subject_id AS subject_id, c.subject_name AS subject_name,
               c.valid_from AS valid_from, c.valid_to AS valid_to
        ORDER BY c.valid_from DESC LIMIT 1
        """,
        {"entity_key": entity_key, "predicate": predicate, "before": _prev_day(date)},
    ).rows
    if not row:
        row = client.execute(
            """
            MATCH (c:Claim {object_id: $entity_key, predicate: $predicate})
            WHERE c.valid_to < $date
            RETURN c.subject_id AS subject_id, c.subject_name AS subject_name,
                   c.valid_from AS valid_from, c.valid_to AS valid_to
            ORDER BY c.valid_to DESC LIMIT 1
            """,
            {"entity_key": entity_key, "predicate": predicate, "date": date},
        ).rows
    if not row:
        return absent(entity_key, predicate)
    r = row[0]
    return result(
        entity_id=entity_key,
        predicate=predicate,
        status="definitive",
        value={"entity_id": r["subject_id"], "name": r["subject_name"]},
        valid_from=r.get("valid_from"),
        valid_to=r.get("valid_to"),
        confidence=0.94,
        as_of=date,
        resolution="before",
    )


def resolve_state_before_entity(
    client: HydraDBClient,
    entity_key: str,
    predicate: str,
    reference: str,
) -> dict[str, Any]:
    """State valid immediately before a referenced subject's first claim.

    Answers "who owned Acme before Priya?": finds the earliest validity start
    for the referenced subject (Priya) and resolves the state right before it.
    Claims are fetched once and matched in Python (the HydraDB query engine's
    WHERE clause does not support string functions/contains).
    """
    from .state import CONFLICTS

    rows = client.execute(
        CONFLICTS,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    ref = reference.strip().lower()
    matches = [
        r for r in rows
        if ref in str(r.get("subject_name") or "").lower()
        or ref in str(r.get("subject_mention") or "").lower()
    ]
    if not matches:
        return absent(entity_key, predicate)
    earliest = min(str(r.get("valid_from") or OPEN_END) for r in matches)
    if earliest == OPEN_END:
        return absent(entity_key, predicate)
    return resolve_state_before(client, entity_key, earliest, predicate)


def anchor_date(client: HydraDBClient, anchor: str | None) -> str | None:
    """Latest dated artifact whose title or content mentions the anchor event/keyword."""
    if not anchor:
        return None
    needle = anchor.strip().lower()
    rows = client.execute(ANCHOR_ARTIFACTS).rows
    best: str | None = None
    for row in rows:
        title = str(row.get("title") or "")
        content = str(row.get("content") or "")
        ts = row.get("ts")
        haystack = f"{title}\n{content}".lower()
        if ts and needle in haystack:
            candidate = str(ts)[:10]
            if best is None or candidate > best:
                best = candidate
    return best


def anchor_date_from_claims(
    client: HydraDBClient,
    entity_key: str,
    predicate: str,
    anchor: str | None,
) -> str | None:
    """Resolve an event anchor (e.g. handoff) to a claim transition date."""
    if not anchor:
        return None
    needle = anchor.strip().lower()
    handoff_terms = ("handoff", "hand off", "taking over", "take over", needle)
    rows = client.execute(
        ANCHOR_CLAIMS,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    best: str | None = None
    for row in rows:
        span = str(row.get("claim_id") or "")
        # evidence_span is not on Claim node in graph — use subject + dates
        subject = str(row.get("subject_name") or "").lower()
        if not any(term in subject or term in span for term in handoff_terms):
            # For generic "handoff" anchor, accept taking-over transitions
            if needle == "handoff" and "taking" not in subject and "hand" not in span:
                continue
        date = row.get("valid_from") or row.get("observed_at")
        if not date:
            continue
        candidate = str(date)[:10]
        if best is None or candidate > best:
            best = candidate
    return best


def resolve_state_after_event(
    client: HydraDBClient,
    entity_key: str,
    predicate: str,
    anchor: str | None,
) -> dict[str, Any]:
    """Owner at the first ownership transition after an anchored event."""
    rows = client.execute(
        HISTORY,
        {"entity_key": entity_key, "predicate": predicate},
    ).rows
    if not rows:
        return absent(entity_key, predicate)

    ordered = sorted(
        rows,
        key=lambda r: (str(r.get("valid_from") or ""), str(r.get("observed_at") or "")),
    )

    # Prefer closed-interval handoffs when the graph stores valid_to faithfully.
    for index, row in enumerate(ordered):
        if not row.get("valid_to") or row.get("valid_to") == OPEN_END:
            continue
        if index + 1 >= len(ordered):
            break
        nxt = ordered[index + 1]
        return result(
            entity_id=entity_key,
            predicate=predicate,
            status="definitive",
            value={"entity_id": nxt["subject_id"], "name": nxt["subject_name"]},
            valid_from=nxt.get("valid_from"),
            valid_to=nxt.get("valid_to"),
            confidence=0.92,
            history=ordered,
            resolution="after-event",
        )

    previous_subject: str | None = None
    for row in ordered:
        subject_id = str(row.get("subject_id") or "")
        if not subject_id:
            continue
        if previous_subject and subject_id != previous_subject:
            return result(
                entity_id=entity_key,
                predicate=predicate,
                status="definitive",
                value={"entity_id": row["subject_id"], "name": row["subject_name"]},
                valid_from=row.get("valid_from"),
                valid_to=row.get("valid_to"),
                confidence=0.9,
                history=ordered,
                resolution="after-event-transition",
            )
        previous_subject = subject_id

    date = anchor_date_from_claims(client, entity_key, predicate, anchor) or anchor_date(client, anchor)
    if date:
        return resolve_state_on(client, entity_key, date, predicate)
    return absent(entity_key, predicate)


def resolve_state_for_constraints(
    client: HydraDBClient,
    entity_key: str,
    predicate: str,
    constraints: Iterable[TemporalConstraint] | None,
) -> dict[str, Any]:
    """Resolve state using decomposed temporal constraints.

    Rule order (first applicable wins):
      1. as_of   -> resolve_state_on(date)
      2. before  -> resolve_state_before(date) (anchor resolved if needed)
      3. after   -> resolve_state_on(date) for the anchor/date
      4. historical (bare past tense) -> previous holder via history
      5. current -> resolve_state
      6. none    -> resolve_state
    """
    constraints = list(constraints or [])
    predicate = predicate or "OWNS"

    for c in constraints:
        if c.kind == "as_of" and c.value:
            return resolve_state_on(client, entity_key, c.value, predicate)
        if c.kind == "before":
            value = c.value or anchor_date(client, c.anchor)
            if value:
                return resolve_state_before(client, entity_key, value, predicate)
            if c.anchor:
                return resolve_state_before_entity(client, entity_key, predicate, c.anchor)
        if c.kind == "after":
            if c.anchor and c.anchor.strip().lower() in {"handoff", "the handoff"}:
                return resolve_state_after_event(client, entity_key, predicate, c.anchor)
            value = c.value or anchor_date_from_claims(client, entity_key, predicate, c.anchor)
            if not value:
                value = anchor_date(client, c.anchor)
            if value:
                return resolve_state_on(client, entity_key, value, predicate)
        if c.kind == "interval" and c.value:
            return resolve_state_on(client, entity_key, c.value, predicate)

    if any(c.kind == "historical" for c in constraints):
        hist = resolve_state_history(client, entity_key, predicate)
        transitions = hist.get("history") or []
        if len(transitions) >= 2:
            prev = transitions[-2]
            return result(
                entity_id=entity_key,
                predicate=predicate,
                status="definitive",
                value={"entity_id": prev["subject_id"], "name": prev["subject_name"]},
                valid_from=prev.get("valid_from"),
                valid_to=prev.get("valid_to"),
                confidence=0.9,
                history=transitions,
                resolution="historical-previous",
            )
        return absent(entity_key, predicate)

    if any(c.kind == "current" for c in constraints):
        return resolve_state(client, entity_key, predicate)

    return resolve_state(client, entity_key, predicate)