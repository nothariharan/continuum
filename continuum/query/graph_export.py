"""Read-only knowledge-graph export for visualization.

Exports the subgraph around one entity (e.g. ``account:acme``) as a simple
node/edge structure using stable business keys. Purely reads the existing
Claim / Artifact / Source / entity graph — no schema change.
"""

from __future__ import annotations

import re
from typing import Any

from continuum.hydradb import HydraDBClient

_READ_PROVENANCE_GRAPH = """
MATCH (c:Claim)-[:ABOUT]->(o {key: $entity_key}),
      (c)-[:SOURCED_FROM]->(a:Artifact)-[:FROM]->(s:Source)
RETURN c.key AS claim_id, c.subject_id AS subject_id, c.subject_name AS subject_name,
       c.predicate AS predicate, c.object_mention AS object_mention,
       c.valid_from AS valid_from, c.observed_at AS observed_at,
       c.evidence_span AS evidence_span,
       a.key AS artifact_id, a.kind AS artifact_kind,
       s.key AS source_id, s.name AS source_name
ORDER BY c.observed_at
"""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "unknown"


def export_graph(client: HydraDBClient, entity_key: str) -> dict[str, Any]:
    """Export the evidence subgraph for one entity as {nodes, edges}."""
    rows = client.execute(_READ_PROVENANCE_GRAPH, {"entity_key": entity_key}).rows

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    nodes[entity_key] = {"id": entity_key, "type": "entity", "name": entity_key.split(":", 1)[-1]}

    def add_node(key: str, type_: str, **props: Any) -> None:
        nodes.setdefault(key, {"id": key, "type": type_, **props})

    def add_edge(source: str, target: str, rel: str) -> None:
        if (source, target, rel) in seen_edges:
            return
        seen_edges.add((source, target, rel))
        edges.append({"source": source, "target": target, "rel": rel})

    for row in rows:
        subject_key = f"person:{_slug(row['subject_name'])}"
        add_node(subject_key, "entity", name=row["subject_name"])
        add_node(row["claim_id"], "claim", predicate=row["predicate"], valid_from=row["valid_from"], evidence=row["evidence_span"])
        add_node(row["artifact_id"], "artifact", kind=row["artifact_kind"])
        add_node(row["source_id"], "source", name=row["source_name"] or row["source_id"])

        add_edge(subject_key, entity_key, row["predicate"])
        add_edge(row["claim_id"], entity_key, "ABOUT")
        add_edge(row["claim_id"], row["artifact_id"], "SOURCED_FROM")
        add_edge(row["artifact_id"], row["source_id"], "FROM")

    return {
        "entity_key": entity_key,
        "nodes": sorted(nodes.values(), key=lambda n: (n["type"], n["id"])),
        "edges": sorted(edges, key=lambda e: (e["rel"], e["source"], e["target"])),
    }
