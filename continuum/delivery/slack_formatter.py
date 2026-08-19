"""Format Continuum answer envelopes for Slack Block Kit.

Product-grade reply: structured `Answer` / `Why` / `State` / `Confidence`
sections built only from the structured envelope (no model text, no CoT).
"""

from __future__ import annotations

from typing import Any

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
    why_lines = _why_lines(evidence)
    state_line = _state_line(state)
    confidence = _confidence_label(status, state.get("confidence"))

    text_lines = [f"Answer: {answer_line}"]
    if sides:
        text_lines.append("Sides:")
        text_lines.extend(f"• {s}" for s in sides)
    if why_lines:
        text_lines.append("Why:")
        text_lines.extend(why_lines)
    if state_line:
        text_lines.append(f"State: {state_line}")
    text_lines.append(f"Confidence: {confidence}")
    text = "\n".join(text_lines)

    blocks: list[dict[str, Any]] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Answer:* {answer_line}"}},
    ]
    if sides:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Sides:*\n" + "\n".join(f"• {s}" for s in sides)},
            }
        )
    if why_lines:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Why:*\n" + "\n".join(why_lines)}},
        )
    if state_line:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*State:* {state_line}"}})
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Confidence:* {confidence}"}})

    return {"text": text, "blocks": blocks}
