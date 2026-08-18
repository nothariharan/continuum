"""Tests for Slack query bot transport (mocked HydraDB/QueryService)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from continuum.delivery.slack_bot import SlackQueryBot, extract_question

RESULT = {
    "question_id": "q1",
    "question": "who owns Acme?",
    "status": "definitive",
    "answer": "Priya",
    "resolved_entities": [],
    "claims_used": [],
    "state_result": {"status": "definitive", "value": {"name": "Priya"}},
    "conflicts": [],
    "evidence": [{"source": "Slack", "observed_at": "2026-07-28"}],
    "layers": {"retrieval": {}, "entity_resolution": {}, "traversal": {}, "state": {}, "evidence_selection": {}},
    "context": {"artifacts": 0, "characters": 0, "tokens_estimate": 0, "claims": 0, "evidence_items": 0},
    "latency_ms": {"retrieval": 0, "entity_resolution": 0, "traversal": 0, "state": 0, "evidence_selection": 0, "total": 0},
    "diagnostics": {},
    "trace": [],
    "query_context": {},
}


def test_extract_question_strips_mentions():
    assert extract_question("<@U123456> who owns Acme?") == "who owns Acme?"
    assert extract_question("<@U123456>  <@U789> who owns Acme?") == "who owns Acme?"
    assert extract_question("plain question") == "plain question"
    assert extract_question("<@U1>") == ""


def test_handle_app_mention_posts_once_and_delegates():
    client = MagicMock()
    posts: list[tuple] = []
    bot = SlackQueryBot(client, post_message=lambda channel, payload, thread_ts: posts.append((channel, payload, thread_ts)))
    with patch("continuum.delivery.query_service.answer", return_value=RESULT) as mock_answer:
        payload = bot.handle_app_mention({"text": "<@U1> who owns Acme?", "channel": "C1", "ts": "1.1"})
    assert len(posts) == 1
    assert posts[0][0] == "C1"
    assert "Priya" in payload["text"]
    assert mock_answer.call_count == 1


def test_empty_question_returns_guidance_without_query():
    client = MagicMock()
    posts: list[tuple] = []
    bot = SlackQueryBot(client, post_message=lambda channel, payload, thread_ts: posts.append(payload))
    with patch("continuum.delivery.query_service.answer") as mock_answer:
        bot.handle_text("<@U1>", channel="C1")
    mock_answer.assert_not_called()
    assert "Ask a question" in posts[0]["text"]
