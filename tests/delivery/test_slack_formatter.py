"""Tests for Slack answer formatter (Batch 3 — structured blocks)."""

from __future__ import annotations

from continuum.delivery.slack_formatter import format_slack_answer, format_slack_trace


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
    text = payload["text"]
    assert "Priya owns Acme now." in text
    assert "Previously: Morgan" in text
    assert "Effective: Aug 1" in text
    assert "Evidence: Slack · Gmail" in text
    assert "Confidence: High" in text
    blocks = payload["blocks"]
    assert len(blocks) >= 3
    # first block is the bold answer line
    assert blocks[0]["type"] == "section"
    assert "Priya owns Acme now." in blocks[0]["text"]["text"]
    # a section carries the Previously / Effective / Evidence metadata
    section_texts = [b["text"]["text"] for b in blocks if b["type"] == "section"]
    assert any("Previously:" in t and "Effective:" in t and "Evidence:" in t for t in section_texts)
    # confidence rendered as a context footer element
    context_texts = [e["text"] for b in blocks if b["type"] == "context" for e in b["elements"]]
    assert any("Confidence" in t for t in context_texts)


def test_trace_checklist_reflects_real_stages():
    payload = format_slack_trace(_definitive())
    text = payload["text"]
    assert "Searching Slack" in text
    assert "Searching Gmail" in text
    assert "Resolving entities" in text
    assert "Checking timeline" in text
    assert "Collecting evidence" in text
    # every stage here has a real signal → all checked
    assert "◦" not in text


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
