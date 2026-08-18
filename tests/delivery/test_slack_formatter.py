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


def test_format_conflict():
    result = {
        "question": "Who owns X?",
        "status": "conflict",
        "answer": None,
        "state_result": {"status": "conflict"},
        "evidence": [],
    }
    payload = format_slack_answer(result)
    assert "conflicting" in payload["text"].lower()


def test_format_historical_answer():
    result = {
        "question": "Who owned Acme before?",
        "status": "definitive",
        "answer": "Morgan",
        "state_result": {"status": "definitive", "resolution": "before", "value": {"name": "Morgan"}},
        "evidence": [{"source": "Gmail", "observed_at": "2026-01-05"}],
    }
    payload = format_slack_answer(result)
    assert "Previous holder: Morgan" in payload["text"]
    assert "Gmail" in payload["text"]
    assert len(payload["blocks"]) >= 2  # answer + evidence block
