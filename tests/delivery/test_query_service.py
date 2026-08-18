"""Tests for QueryService (mocked HydraDB)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from continuum.delivery.query_service import QueryService


def test_ask_delegates_to_benchmark_answer():
    client = MagicMock()
    client.database = "default"
    with patch("continuum.delivery.query_service.answer") as mock_answer:
        mock_answer.return_value = {
            "question_id": "q1",
            "question": "Who owns Acme?",
            "status": "definitive",
            "answer": "Priya",
            "resolved_entities": [],
            "claims_used": [],
            "state_result": {"status": "definitive", "value": {"name": "Priya"}},
            "conflicts": [],
            "evidence": [],
            "layers": {
                "retrieval": {},
                "entity_resolution": {},
                "traversal": {},
                "state": {},
                "evidence_selection": {},
            },
            "context": {"artifacts": 0, "characters": 0, "tokens_estimate": 0, "claims": 0, "evidence_items": 0},
            "latency_ms": {"retrieval": 0, "entity_resolution": 0, "traversal": 0, "state": 0, "evidence_selection": 0, "total": 0},
            "diagnostics": {},
            "trace": [],
            "query_context": {},
        }
        service = QueryService(client)
        result = service.ask("Who owns Acme?", question_id="q1")
        assert result["answer"] == "Priya"
        mock_answer.assert_called_once()


def test_api_ask_parses_json_body():
    """Regression: AskRequest must be recognized as a body model (was misrouted to query params)."""
    pytest = __import__("pytest")
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from continuum.delivery.api import create_app

    client = MagicMock()
    client.database = "default"
    service = QueryService(client)
    with patch("continuum.delivery.query_service.answer") as mock_answer:
        mock_answer.return_value = {
            "question_id": "q1", "question": "x", "status": "absent", "answer": None,
            "resolved_entities": [], "claims_used": [], "state_result": {"status": "absent", "value": None},
            "conflicts": [], "evidence": [],
            "layers": {"retrieval": {}, "entity_resolution": {}, "traversal": {}, "state": {}, "evidence_selection": {}},
            "context": {"artifacts": 0, "characters": 0, "tokens_estimate": 0, "claims": 0, "evidence_items": 0},
            "latency_ms": {"retrieval": 0, "entity_resolution": 0, "traversal": 0, "state": 0, "evidence_selection": 0, "total": 0},
            "diagnostics": {}, "trace": [], "query_context": {},
        }
        app = create_app(service=service)
        resp = TestClient(app).post("/v1/ask", json={"question": "Who owns Acme?", "question_id": "q1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "absent"
    assert mock_answer.call_count == 1
    call = mock_answer.call_args
    assert call.args[0] is client
    assert call.args[1] == {"question_id": "q1", "question": "Who owns Acme?"}
