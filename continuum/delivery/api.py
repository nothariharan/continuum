"""Optional FastAPI HTTP wrapper for QueryService."""

import os
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
    # Allowed origins: localhost by default, plus any set via
    # CONTINUUM_ALLOWED_ORIGINS (comma-separated) for the deployed frontend.
    _default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    _env_origins = [o.strip() for o in os.environ.get("CONTINUUM_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    _allowed = _env_origins or _default_origins
    _allow_all = "*" in _allowed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if _allow_all else [*_default_origins, *_env_origins],
        allow_origin_regex=None,
        allow_credentials=not _allow_all,
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

    @app.get("/v1/connectors")
    def connectors() -> dict[str, Any]:
        """Real connector state — configured creds + indexed volume from HydraDB.

        Never fabricates data: counts come from the graph; a connector is
        'connected' only when its credentials are configured AND it has indexed
        artifacts, otherwise 'demo'.
        """
        def _count(query: str, params: dict[str, Any] | None = None) -> int:
            if _client is None:
                return 0
            try:
                rows = _client.execute(query, params or {}).rows
                return int(rows[0]["n"]) if rows else 0
            except Exception:  # noqa: BLE001
                return 0

        total_artifacts = _count("MATCH (a:Artifact) RETURN count(*) AS n")
        slack_configured = bool(os.environ.get("SLACK_BOT_TOKEN"))
        gmail_configured = bool(os.environ.get("GMAIL_TOKEN")) or os.path.exists("gmail_token.json")

        def _src_count(source_id: str) -> int:
            return _count(
                "MATCH (a:Artifact)-[:FROM]->(s:Source {key: $sid}) RETURN count(*) AS n",
                {"sid": source_id},
            )

        slack_n = _src_count("source:slack")
        gmail_n = _src_count("source:gmail")

        def _status(configured: bool, n: int) -> str:
            if configured and n > 0:
                return "connected"
            if n > 0:
                return "demo"
            return "planned"

        return {
            "mode": "live" if total_artifacts > 0 else "demo",
            "total_artifacts": total_artifacts,
            "connectors": [
                {"id": "slack", "name": "Slack", "status": _status(slack_configured, slack_n),
                 "artifacts": slack_n, "configured": slack_configured},
                {"id": "gmail", "name": "Gmail", "status": _status(gmail_configured, gmail_n),
                 "artifacts": gmail_n, "configured": gmail_configured},
            ],
        }

    return app
