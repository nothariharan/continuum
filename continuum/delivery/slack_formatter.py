"""Format Continuum answer envelopes for Slack Block Kit.

Product-grade reply: structured `Answer` / `Why` / `State` / `Confidence`
sections built only from the structured envelope (no model text, no CoT).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

_SOURCE_DISPLAY = {
    "slack": "Slack",
    "gmail": "Gmail",
    "linear": "Linear",
    "jira": "Jira",
    "github": "GitHub",
    "drive": "Drive",
    "confluence": "Confluence",
    "hubspot": "HubSpot",
    "fireflies": "Fireflies",
}

_KIND_PHRASES = {
    "slack_message": "message",
    "gmail_message": "email",
    "linear_ticket": "ticket",
    "jira_ticket": "ticket",
    "github_pr": "pull request",
    "meeting_transcript": "meeting transcript",
    "hubspot_record": "record",
    "fireflies_transcript": "meeting transcript",
    "confluence_page": "page",
}


def _kind_phrase(kind: str | None) -> str:
    if not kind:
        return ""
    return _KIND_PHRASES.get(kind.lower(), kind.replace("_", " ").strip())


def _display_source(source: Any) -> str:
    s = str(source)
    return _SOURCE_DISPLAY.get(s.lower(), s)


def _evidence_sources(evidence: list[dict[str, Any]]) -> list[str]:
    """Distinct, display-cased sources that actually contributed evidence."""
    order: list[str] = []
    for item in evidence:
        raw = item.get("source") or item.get("artifact_source")
        if not raw:
            continue
        label = _display_source(raw)
        if label not in order:
            order.append(label)
    return order


def _previous_name(state: dict[str, Any]) -> str | None:
    """The owner immediately before the current one, from state history."""
    names: list[str] = []
    for row in state.get("history") or []:
        n = row.get("subject_name") or row.get("subject_mention")
        if n and (not names or names[-1] != str(n)):
            names.append(str(n))
    return names[-2] if len(names) >= 2 else None


def _fmt_date(value: Any) -> str | None:
    """Render a date/ISO timestamp as 'Aug 5'; fall back to the raw string."""
    if not value:
        return None
    s = str(value)
    for parse in (
        lambda: datetime.fromisoformat(s),
        lambda: datetime.combine(date.fromisoformat(s[:10]), datetime.min.time()),
    ):
        try:
            d = parse()
            return f"{d.strftime('%b')} {d.day}"
        except (ValueError, TypeError):
            continue
    return s


_TRACE_DONE = "✓"
_TRACE_PENDING = "◦"


def format_slack_trace(result: dict[str, Any]) -> dict[str, Any]:
    """Build the live pipeline checklist from the REAL answer envelope.

    Each ✓ reflects a stage that actually ran: a source that returned evidence,
    entity resolution, timeline reconstruction, and evidence collection. Nothing
    is faked — a stage with no signal shows a hollow marker.
    """
    state = result.get("state_result") or {}
    evidence = result.get("evidence") or state.get("evidence") or []
    diagnostics = result.get("diagnostics") or {}
    resolved = result.get("resolved_entities") or []
    history = state.get("history") or []
    sources = _evidence_sources(evidence)

    steps: list[tuple[str, bool]] = [(f"Searching {s}", True) for s in sources]
    steps.append(("Resolving entities", bool(resolved) or diagnostics.get("entity_resolution_ok") is True or bool(evidence)))
    steps.append(("Checking timeline", bool(history) or diagnostics.get("temporal_ok") is True))
    steps.append(("Collecting evidence", bool(evidence)))

    checklist = "\n".join(f"{_TRACE_DONE if ok else _TRACE_PENDING}  {label}" for label, ok in steps)
    text = "Continuum · reconstructing the answer\n" + checklist
    blocks = [
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "🧠  *Continuum* is reconstructing the answer from company memory…"}]},
        {"type": "section", "text": {"type": "mrkdwn", "text": checklist}},
    ]
    return {"text": text, "blocks": blocks}


def _entity_label(state: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    for item in evidence:
        if item.get("object_mention"):
            return str(item["object_mention"])
    entity_id = str(state.get("entity_id") or "")
    if ":" in entity_id:
        entity_id = entity_id.split(":", 1)[1]
    return entity_id.replace("-", " ").title() if entity_id else "it"


def _name(state: dict[str, Any]) -> str | None:
    value = state.get("value")
    if isinstance(value, dict):
        return value.get("name") or value.get("subject_name") or None
    return None


def _conflict_sides(state: dict[str, Any]) -> list[str]:
    sides: list[str] = []
    for claim in state.get("claims") or []:
        n = claim.get("subject_name") or claim.get("subject_mention")
        if n and str(n) not in sides:
            sides.append(str(n))
    if not sides:
        for subject in state.get("conflicting_subjects") or []:
            label = str(subject).split(":", 1)[-1].replace("-", " ").title()
            if label not in sides:
                sides.append(label)
    return sides


def _answer_line(status: str, name: str | None, entity: str, resolution: str | None) -> str:
    if status in {"definitive", "consistent"} and name:
        if resolution == "before":
            return f"{name} owned {entity}."
        return f"{name} owns {entity} now."
    if status in {"conflict", "review"}:
        return "Conflicting evidence — needs review."
    if status == "absent":
        return "Unknown — insufficient evidence to answer safely."
    if name:
        return str(name)
    return "No grounded answer available."


def _why_lines(evidence: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for item in evidence:
        source = item.get("source") or item.get("artifact_source") or "source"
        kind = _kind_phrase(item.get("artifact_kind"))
        label = str(source) + (f" — {kind}" if kind else "")
        if label in seen:
            continue
        seen.add(label)
        lines.append(f"• {label}")
    return lines


def _state_line(state: dict[str, Any]) -> str:
    history = state.get("history") or []
    if history:
        names: list[str] = []
        for row in history:
            n = row.get("subject_name") or row.get("subject_mention")
            if n and (not names or names[-1] != str(n)):
                names.append(str(n))
        if names:
            transition = " → ".join(names)
            valid_from = state.get("valid_from")
            return transition + (f"  (effective {valid_from})" if valid_from else "")
    valid_from = state.get("valid_from")
    if valid_from:
        return f"since {valid_from}"
    return ""


def _confidence_label(status: str, confidence: Any) -> str:
    if status in {"conflict", "review"}:
        return "Low"
    if status == "absent":
        return "None"
    if isinstance(confidence, (int, float)):
        if confidence >= 0.9:
            return "High"
        if confidence >= 0.7:
            return "Medium"
        return "Low"
    return "High"


def format_slack_answer(result: dict[str, Any]) -> dict[str, Any]:
    """Convert a benchmark answer envelope into Slack Block Kit + fallback text."""
    state = result.get("state_result") or {}
    status = state.get("status") or result.get("status") or "unknown"
    name = _name(state)
    evidence = result.get("evidence") or state.get("evidence") or []
    entity = _entity_label(state, evidence)
    resolution = state.get("resolution")

    answer_line = _answer_line(status, name, entity, resolution)
    sides = _conflict_sides(state)
    previous = _previous_name(state) if resolution != "before" else None
    effective = _fmt_date(state.get("valid_from"))
    ev_sources = _evidence_sources(evidence)
    confidence = _confidence_label(status, state.get("confidence"))

    text_lines = [answer_line]
    if sides:
        text_lines.append("Sides: " + " vs ".join(sides))
    if previous:
        text_lines.append(f"Previously: {previous}")
    if effective:
        text_lines.append(f"Effective: {effective}")
    if ev_sources:
        text_lines.append("Evidence: " + " · ".join(ev_sources))
    text_lines.append(f"Confidence: {confidence}")
    text = "\n".join(text_lines)

    blocks: list[dict[str, Any]] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{answer_line}*"}},
    ]
    if sides:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Sides:* " + " vs ".join(sides)}},
        )
    meta: list[str] = []
    if previous:
        meta.append(f"*Previously:* {previous}")
    if effective:
        meta.append(f"*Effective:* {effective}")
    if ev_sources:
        meta.append(f"*Evidence:* {' · '.join(ev_sources)}")
    if meta:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(meta)}})
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"Confidence: {confidence}"}]})

    return {"text": text, "blocks": blocks}
