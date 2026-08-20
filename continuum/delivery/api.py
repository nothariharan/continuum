"""Optional FastAPI HTTP wrapper for QueryService."""

from typing import Any

from continuum.delivery.query_service import QueryService
from continuum.query.graph_export import export_graph as _export_graph
from continuum.delivery.slack_formatter import format_slack_answer
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient
from continuum.query.semantic import StateQueryAdapter


def create_app(service: QueryService | None = None):
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
    except ImportError as exc:
        raise ImportError("Install optional delivery deps: pip install fastapi uvicorn") from exc

    app = FastAPI(title="Continuum Query API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _service = service
    _client: HydraDBClient | None = None
    _adapter: StateQueryAdapter | None = None

    class AskRequest(BaseModel):
        question: str
        question_id: str = "http-ad-hoc"

    @app.on_event("startup")
    def _startup() -> None:
        nonlocal _service, _adapter, _client
        if _service is None:
            client = HydraDBClient()
            client.health_check()
            _client = client
            _service = QueryService(client)
            _adapter = StateQueryAdapter(client, entity_store=EntityStore(client))

    @app.get("/health")
    def health() -> dict[str, Any]:
        assert _service is not None
        return _service.health()

    @app.post("/v1/ask")
    def ask(body: AskRequest) -> dict[str, Any]:
        assert _service is not None
        return _service.ask(body.question, question_id=body.question_id)

    @app.post("/v1/ask/formatted")
    def ask_formatted(body: AskRequest) -> dict[str, Any]:
        assert _service is not None
        result = _service.ask(body.question, question_id=body.question_id)
        return format_slack_answer(result)

    @app.get("/v1/graph/export")
    def graph_export(
        entity: str = Query(..., description="Canonical entity key, e.g. account:acme"),
        depth: int = Query(2, ge=1, le=4),
    ) -> dict[str, Any]:
        # Use the canonical query-layer exporter (single source of truth) and
        # adapt it to the web GraphExport contract. `depth` reserved for future use.
        assert _client is not None
        _ = depth
        raw = _export_graph(_client, entity)
        nodes = [
            {
                "id": n["id"],
                "type": n.get("type", "entity"),
                "label": n.get("type", "entity"),
                "name": n.get("name") or n.get("kind") or n["id"],
                **({"source": n["source"]} if n.get("source") else {}),
                **({"dsid": n["id"]} if n.get("type") == "artifact" else {}),
            }
            for n in raw.get("nodes", [])
        ]
        edges = [
            {
                "source": e["source"],
                "target": e["target"],
                "predicate": e.get("rel") or e.get("predicate") or "",
                **({"claim_id": e["claim_id"]} if e.get("claim_id") else {}),
            }
            for e in raw.get("edges", [])
        ]
        return {"entity": entity, "nodes": nodes, "edges": edges}

    @app.get("/v1/semantic/history")
    def semantic_history(
        entity: str = Query(...),
        predicate: str = Query("OWNS"),
    ) -> dict[str, Any]:
        if _adapter is None:
            raise HTTPException(status_code=503, detail="semantic adapter unavailable")
        return _adapter.get_history(entity, predicate)

    @app.get("/v1/semantic/evidence")
    def semantic_evidence(
        entity: str = Query(...),
        predicate: str = Query("OWNS"),
    ) -> dict[str, Any]:
        if _adapter is None:
            raise HTTPException(status_code=503, detail="semantic adapter unavailable")
        return _adapter.get_evidence(entity, predicate)

    @app.get("/v1/semantic/conflicts")
    def semantic_conflicts(
        entity: str = Query(...),
        predicate: str = Query("OWNS"),
    ) -> dict[str, Any]:
        if _adapter is None:
            raise HTTPException(status_code=503, detail="semantic adapter unavailable")
        return _adapter.get_conflicts(entity, predicate)

    @app.get("/v1/semantic/state")
    def semantic_state(
        entity: str = Query(...),
        predicate: str = Query("OWNS"),
    ) -> dict[str, Any]:
        if _adapter is None:
            raise HTTPException(status_code=503, detail="semantic adapter unavailable")
        return _adapter.get_current_state(entity, predicate)

    return app
