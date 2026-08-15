"""Load normalized Artifacts into HydraDB as :Artifact nodes and read them back.

Phase 2A only: stores artifacts as nodes. No claims graph, no entity resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Iterable

from continuum.hydradb import HydraDBClient

CREATE_ARTIFACT = """
UNWIND $rows AS row
MERGE (a {id: row.dsid})
SET a:Artifact,
    a.dsid = row.dsid_key,
    a.source = row.source,
    a.type = row.type,
    a.author = row.author,
    a.timestamp = row.timestamp,
    a.title = row.title,
    a.content_length = row.content_length,
    a.noise = row.noise,
    a.ingested_at = row.ingested_at
"""

READ_ARTIFACT = """
MATCH (a:Artifact {id: $id})
RETURN a.dsid AS dsid, a.source AS source, a.type AS type,
       a.author AS author, a.timestamp AS timestamp,
       a.title AS title, a.content_length AS content_length,
       a.noise AS noise
"""

READ_ARTIFACTS = """
MATCH (a:Artifact)
RETURN a.id AS id, a.dsid AS dsid, a.source AS source
ORDER BY a.id
"""

DELETE_ALL_ARTIFACTS = """
MATCH (a:Artifact)
WHERE a.id >= $min_id AND a.id <= $max_id
DETACH DELETE a
"""

DELETE_LOW_ARTIFACTS = """
MATCH (a:Artifact)
WHERE a.id >= 0 AND a.id <= 2000000
DETACH DELETE a
"""

COUNT_ARTIFACTS = """
MATCH (a:Artifact) RETURN count(*) AS n
"""

COUNT_ARTIFACTS_RANGE = """
MATCH (a:Artifact)
WHERE a.id >= $min_id AND a.id < $max_id
RETURN count(*) AS n
"""


@dataclass(frozen=True)
class LoadResult:
    attempted: int
    written: int
    load_ms: float
    read_back_ms: float
    read_back_count: int


ID_OFFSET = 1_000_000_000


def _to_row(artifact: dict[str, Any], ingested_at: str, dsid_to_id: dict[str, int]) -> dict[str, Any]:
    metadata = artifact.get("metadata") or {}
    return {
        "dsid": dsid_to_id[artifact["id"]],
        "dsid_key": artifact["id"],
        "source": artifact["source"],
        "type": artifact["type"],
        "author": artifact.get("author") or "",
        "timestamp": artifact.get("timestamp") or "",
        "title": artifact.get("title") or "",
        "content_length": len(artifact.get("content") or ""),
        "noise": bool(metadata.get("noise")),
        "ingested_at": ingested_at,
    }


def load_artifacts(
    client: HydraDBClient,
    artifacts: Iterable[dict[str, Any]],
    chunk_size: int = 100,
) -> LoadResult:
    artifact_list = list(artifacts)
    dsid_to_id = {a["id"]: ID_OFFSET + index for index, a in enumerate(artifact_list, start=1)}
    rows = [_to_row(a, "phase2a", dsid_to_id) for a in artifact_list]
    total = len(rows)
    started = perf_counter()
    for i in range(0, total, chunk_size):
        chunk = rows[i : i + chunk_size]
        client.execute_batch(CREATE_ARTIFACT, chunk)
    load_ms = (perf_counter() - started) * 1000

    started = perf_counter()
    read_back = client.execute(READ_ARTIFACTS).rows
    read_ms = (perf_counter() - started) * 1000
    return LoadResult(
        attempted=total,
        written=total,
        load_ms=load_ms,
        read_back_ms=read_ms,
        read_back_count=len(read_back),
    )


def read_artifact(client: HydraDBClient, artifact_id: int) -> dict[str, Any] | None:
    rows = client.execute(READ_ARTIFACT, {"id": artifact_id}).rows
    return rows[0] if rows else None


def count_artifacts(client: HydraDBClient) -> int:
    return int(client.execute(COUNT_ARTIFACTS).rows[0]["n"])


def count_artifacts_in_range(client: HydraDBClient, min_id: int, max_id: int) -> int:
    """Count :Artifact nodes in [min_id, max_id). Used by tests so Phase 1
    fixture artifacts (string-keyed, low ids) and Phase 2B fixture artifacts
    (1e12+) do not leak into the Phase 2A real-dataset count."""
    return int(client.execute(COUNT_ARTIFACTS_RANGE, {"min_id": min_id, "max_id": max_id}).rows[0]["n"])


def delete_all_artifacts(client: HydraDBClient) -> None:
    """Delete every :Artifact node: low ids in one pass, Phase 2A range chunked.

    Chunk size 25 keeps each range delete well under the 30 s query limit
    (deletes run ~155 ms/node on this runtime).
    """
    client.execute(DELETE_LOW_ARTIFACTS)
    step = 25
    for low in range(ID_OFFSET, ID_OFFSET + 100_000, step):
        client.execute(
            DELETE_ALL_ARTIFACTS,
            {"min_id": low, "max_id": low + step - 1},
        )