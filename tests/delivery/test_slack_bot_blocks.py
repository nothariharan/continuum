"""Batch 3 — Slack Block Kit answer blocks (presentation, no reasoning leakage).

Given a canned `answer()` envelope (definitive / conflict / abstain), the
Block Kit payload has the right sections and contains no chain-of-thought or
raw model reasoning strings.
"""

from __future__ import annotations

from continuum.delivery.slack_formatter import format_slack_answer

_REASONING_MARKERS = (
    "i think",
    "reasoning",
    "step 1",
    "step 2",
    "chain of thought",
    "cot",
    "because",
    "therefore",
    "however",
    "let me",
    "based on the",
    "to answer this",
    "internal",
)


def _envelope(**state_overrides) -> dict:
    state = {
        "entity_id": "account:acme",
        "predicate": "OWNS",
        "status": "definitive",
        "value": {"entity_id": "person:priya", "name": "Priya"},
        "valid_from": "2026-08-01",
        "confidence": 0.96,
    }
    state.update(state_overrides)
    return {
        "question": "Who owns Acme?",
        "status": state["status"],
        "answer": "Priya",
        "state_result": state,
        "evidence": [
            {"source": "Slack", "artifact_kind": "slack_message", "object_mention": "Acme"},
            {"source": "Linear", "artifact_kind": "linear_ticket", "object_mention": "Acme"},
        ],
    }


def _all_text(payload: dict) -> str:
    blocks_text = " ".join(b.get("text", {}).get("text", "") for b in payload.get("blocks", []))
    return (payload.get("text", "") + " " + blocks_text).lower()


def test_definitive_has_no_reasoning_strings():
    payload = format_slack_answer(_envelope())
    text = _all_text(payload)
    for marker in _REASONING_MARKERS:
        assert marker not in text, f"reasoning marker leaked: {marker!r} in {text!r}"


def test_conflict_has_no_reasoning_strings():
    payload = format_slack_answer(
        _envelope(
            status="conflict",
            value=None,
            conflicting_subjects=["person:morgan", "person:priya"],
            claims=[{"subject_name": "Morgan"}, {"subject_name": "Priya"}],
        )
    )
    text = _all_text(payload)
    for marker in _REASONING_MARKERS:
        assert marker not in text, f"reasoning marker leaked: {marker!r} in {text!r}"


def test_abstain_has_no_reasoning_strings():
    payload = format_slack_answer(_envelope(status="absent", value=None, confidence=None))
    text = _all_text(payload)
    for marker in _REASONING_MARKERS:
        assert marker not in text, f"reasoning marker leaked: {marker!r} in {text!r}"


def test_every_block_is_valid_section_or_context():
    for env in (
        _envelope(),
        _envelope(status="conflict", value=None, conflicting_subjects=["person:x"]),
        _envelope(status="absent", value=None),
    ):
        payload = format_slack_answer(env)
        for block in payload["blocks"]:
            assert block["type"] in ("section", "context")
            if block["type"] == "section":
                assert block["text"]["type"] == "mrkdwn"
                assert block["text"]["text"].strip()
            else:
                assert block["elements"]
                for element in block["elements"]:
                    assert element["type"] == "mrkdwn"
                    assert element["text"].strip()
