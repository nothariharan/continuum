"""Tests for Slack answer formatter."""

from __future__ import annotations

from continuum.delivery.slack_formatter import format_slack_answer


def test_format_definitive_answer():
    result = {
        "question": "Who owns Acme?",
        "status": "definitive",
        "answer": "Priya",
        "state_result": {"status": "definitive", "value": {"name": "Priya"}},
        "evidence": [{"source": "Slack", "observed_at": "2026-07-28"}],
    }
    payload = format_slack_answer(result)
    assert "Priya" in payload["text"]
    assert payload["blocks"]


def test_format_abstention():
    result = {
        "question": "Who owns X?",
        "status": "absent",
        "state_result": {"status": "absent"},
        "evidence": [],
    }
    payload = format_slack_answer(result)
    assert "Unknown" in payload["text"] or "insufficient" in payload["text"]
