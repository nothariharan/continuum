"""Minimal Bolt transport adapter; no graph models or ORM live here."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Iterable, Mapping

from neo4j import GraphDatabase

from .config import HydraDBConfig


def _allow_hydradb_server_product() -> None:
    """HydraDB advertises SlateDBGraph/*; official neo4j 5.x driver rejects it."""
    try:
        import neo4j._sync.io._common as bolt_common
    except ImportError:
        return
    original = getattr(bolt_common, "check_supported_server_product", None)
    if original is None or not callable(original):
        return

    def _patched(agent: str) -> None:
        if str(agent).startswith("SlateDBGraph/"):
            return
        original(agent)

    if getattr(bolt_common.check_supported_server_product, "__name__", "") != "_patched":
        bolt_common.check_supported_server_product = _patched  # type: ignore[assignment]


_allow_hydradb_server_product()


@dataclass(frozen=True)
class QueryResult:
    rows: list[dict[str, Any]]
    elapsed_ms: float


class HydraDBClient:
    def __init__(self, config: HydraDBConfig | None = None) -> None:
        self.config = config or HydraDBConfig.from_env()
        self._driver = GraphDatabase.driver(
            self.config.bolt_uri,
            auth=(self.config.user, self.config.password),
        )

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "HydraDBClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def health_check(self) -> bool:
        self._driver.verify_connectivity()
        with self._driver.session(database=self.config.database) as session:
            session.run(
                "MATCH (n:ContinuumHealthProbe {id: 1}) RETURN n.id AS id"
            ).consume()
        return True

    def execute(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> QueryResult:
        started = perf_counter()
        with self._driver.session(database=self.config.database) as session:
            result = session.run(query, parameters or {})
            rows = [record.data() for record in result]
            result.consume()
        return QueryResult(rows=rows, elapsed_ms=(perf_counter() - started) * 1000)

    def execute_batch(
        self,
        query: str,
        rows: Iterable[Mapping[str, Any]],
    ) -> QueryResult:
        return self.execute(query, {"rows": list(rows)})
