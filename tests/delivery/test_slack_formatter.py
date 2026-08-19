"""Tests for Slack answer formatter (Batch 3 — structured blocks)."""

from __future__ import annotations

from continuum.delivery.slack_formatter import format_slack_answer


def _definitive(**overrides) -> dict:
    result = {
        "question": "Who owns Acme?",
        "status": "definitive",
        "answer": "Priya",
        "state_result": {
            "entity_id": "account:acme",
            "predicate": "OWNS",
            "status": "definitive",
            "value": {"entity_id": "person:priya", "name": "Priya"},
            "valid_from": "2026-08-01",
            "confidence": 0.96,
            "history": [
                {"subject_name": "Morgan", "valid_from": "2026-07-01"},
                {"subject_name": "Priya", "valid_from": "2026-08-01"},
            ],
        },
        "evidence": [
            {"source": "Slack", "artifact_kind": "slack_message", "object_mention": "Acme", "observed_at": "2026-08-01"},
            {"source": "Gmail", "artifact_kind": "gmail_message", "object_mention": "Acme", "observed_at": "2026-08-02"},
        ],
    }
    result.update(overrides)
    return result


def test_definitive_answer_sections():
    payload = format_slack_answer(_definitive())
    assert "Priya owns Acme now." in payload["text"]
    assert "Why:" in payload["text"]
    assert "Slack — message" in payload["text"]
    assert "Gmail — email" in payload["text"]
    assert "State: Morgan → Priya" in payload["text"]
    assert "Confidence: High" in payload["text"]
    blocks = payload["blocks"]
    assert len(blocks) >= 4
    headings = [b["text"]["text"] for b in blocks]
    assert any(h.startswith("*Answer:*") for h in headings)
    assert any(h.startswith("*Why:*") for h in headings)
    assert any(h.startswith("*State:*") for h in headings)
    assert any(h.startswith("*Confidence:*") for h in headings)


def test_absent_is_honest():
    payload = format_slack_answer(
        {"state_result": {"entity_id": "account:acme", "status": "absent"}, "evidence": []}
    )
    assert "insufficient" in payload["text"] or "Unknown" in payload["text"]
    assert "Confidence: None" in payload["text"]


def test_conflict_shows_both_sides():
    payload = format_slack_answer(
        {
            "state_result": {
                "entity_id": "account:acme",
                "status": "conflict",
                "conflicting_subjects": ["person:morgan", "person:priya"],
                "claims": [
                    {"subject_name": "Morgan"},
                    {"subject_name": "Priya"},
                ],
            },
            "evidence": [],
        }
    )
    assert "conflicting" in payload["text"].lower()
    assert "Morgan" in payload["text"] and "Priya" in payload["text"]
    assert "Confidence: Low" in payload["text"]


def test_historical_answer_uses_before_phrasing():
    payload = format_slack_answer(
        {
            "state_result": {
                "entity_id": "account:acme",
                "status": "definitive",
                "resolution": "before",
                "value": {"entity_id": "person:morgan", "name": "Morgan"},
                "confidence": 0.9,
            },
            "evidence": [{"source": "Gmail", "artifact_kind": "gmail_message", "object_mention": "Acme"}],
        }
    )
    assert "Morgan owned Acme." in payload["text"]
    assert "Gmail" in payload["text"]
