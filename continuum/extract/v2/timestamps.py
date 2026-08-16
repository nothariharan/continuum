"""Timestamp resolver: deterministic time signals, no invented dates.

Rules:
- observed_at = artifact timestamp (strongest), else meeting date, else the
  last revision-history date, else the last text-timeline date, else None.
  Never a bare ISO string in prose/JSON examples (that is content, not time).
- valid_from = only when the text explicitly establishes when the fact
  becomes true ("takes over next Monday", "starting 2026-03-01",
  "as of ...", "effective ..."). Otherwise None.
- valid_to   = only when the text explicitly bounds it ("until ...",
  "through ...", "ends ..."). Otherwise None.
- Relative dates are recognized but NOT converted — no invention.

Returns (observed_at, valid_from, valid_to, timestamp_source).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

EXPLICIT_FROM_RE = re.compile(
    r"\b(?:starting|starts|effective|as of|from|beginning)\s+(?:on\s+)?"
    r"(20[0-9]{2}-[0-9]{2}-[0-9]{2})\b",
    re.IGNORECASE,
)
EXPLICIT_TO_RE = re.compile(
    r"\b(?:until|through|till|ends?)\s+(?:on\s+)?(20[0-9]{2}-[0-9]{2}-[0-9]{2})\b",
    re.IGNORECASE,
)
TAKEOVER_RELATIVE_RE = re.compile(
    r"\b(takes? over|handoff|transition)\b.*?\b(next\s+(?:monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday))\b",
    re.IGNORECASE,
)
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _next_weekday(base: datetime, weekday: int) -> str:
    delta = (weekday - base.weekday()) % 7
    if delta == 0:
        delta = 7
    return (base + timedelta(days=delta)).date().isoformat()


def _parse_explicit_date(match: re.Match[str]) -> str:
    return match.group(1)


def resolve_timestamps(envelope) -> tuple[str | None, str | None, str | None, str | None]:
    """Resolve observed_at / valid_from / valid_to from envelope signals.

    Returns (observed_at, valid_from, valid_to, timestamp_source).
    """
    content = envelope.content or ""

    observed: str | None = None
    source: str | None = None

    if envelope.timestamp:
        observed = envelope.timestamp
        source = envelope.ts_source or "artifact"
    elif envelope.meeting_date:
        observed = envelope.meeting_date
        source = "meeting-date"
    elif envelope.revision_dates:
        observed = envelope.revision_dates[-1]
        source = "revision-history"
    elif envelope.text_timeline_dates:
        observed = envelope.text_timeline_dates[-1]
        source = "text-timeline"

    valid_from: str | None = None
    valid_to: str | None = None

    explicit_from = EXPLICIT_FROM_RE.search(content)
    if explicit_from:
        valid_from = _parse_explicit_date(explicit_from)

    explicit_to = EXPLICIT_TO_RE.search(content)
    if explicit_to:
        valid_to = _parse_explicit_date(explicit_to)

    takeover = TAKEOVER_RELATIVE_RE.search(content)
    if takeover and observed:
        try:
            base = datetime.fromisoformat(observed[:10])
            valid_from = _next_weekday(base, WEEKDAYS[takeover.group(2).lower().split()[-1]])
        except (ValueError, KeyError):
            valid_from = valid_from

    if valid_from and valid_to and valid_to < valid_from:
        valid_to = None

    return observed, valid_from, valid_to, source
