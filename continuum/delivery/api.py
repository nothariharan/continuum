"""Optional FastAPI HTTP wrapper for QueryService."""

from __future__ import annotations

from typing import Any

from continuum.delivery.query_service import QueryService
from continuum.hydradb import HydraDBClient


def create_app(service: QueryService | None = None):
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
    except ImportError as exc:
        raise ImportError("Install optional delivery deps: pip install fastapi uvicorn") from exc

    app = FastAPI(title="Continuum Query API", version="1.0.0")
    _service = service

    class AskRequest(BaseModel):
        question: str
        question_id: str = "http-ad-hoc"

    @app.on_event("startup")
    def _startup() -> None:
        nonlocal _service
        if _service is None:
            client = HydraDBClient()
            client.health_check()
            _service = QueryService(client)

    @app.get("/health")
    def health() -> dict[str, Any]:
        assert _service is not None
        return _service.health()

    @app.post("/v1/ask")
    def ask(body: AskRequest) -> dict[str, Any]:
        assert _service is not None
        return _service.ask(body.question, question_id=body.question_id)

    return app
