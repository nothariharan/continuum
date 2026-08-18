"""Format Continuum answer envelopes for Slack Block Kit."""

from __future__ import annotations

from typing import Any


def format_slack_answer(result: dict[str, Any]) -> dict[str, Any]:
    """Convert benchmark pipeline result to Slack blocks + fallback text."""
    lines: list[str] = []
    state = result.get("state_result") or {}
    status = state.get("status") or result.get("status") or "unknown"
    answer = result.get("answer") or ""

    if status == "definitive" and state.get("value"):
        name = state["value"].get("name") or state["value"].get("subject_name") or answer
        lines.append(f"{name} owns it now." if "owns" in result.get("question", "").lower() else str(name))
    elif status in {"conflict", "review"}:
        lines.append("Multiple conflicting claims — review required before answering.")
    elif status == "absent":
        lines.append("Unknown — insufficient evidence to answer safely.")
    elif answer:
        lines.append(answer)
    else:
        lines.append("No grounded answer available.")

    if state.get("resolution") == "before" and state.get("value"):
        lines.append(f"Previous holder: {state['value'].get('name', 'unknown')}")

    evidence = result.get("evidence") or []
    if evidence:
        lines.append("Sources:")
        for item in evidence[:5]:
            source = item.get("source") or item.get("artifact_source") or "source"
            observed = item.get("observed_at") or item.get("timestamp") or ""
            lines.append(f"• {source}, {observed}".rstrip(", "))

    text = "\n".join(lines)
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text.replace("\n", "\n")}},
    ]
    if evidence:
        bullets = []
        for item in evidence[:5]:
            source = item.get("source") or "source"
            url = item.get("source_url") or item.get("artifact_id")
            bullets.append(f"• *{source}* — `{url}`")
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(bullets)}})

    return {"text": text, "blocks": blocks}
