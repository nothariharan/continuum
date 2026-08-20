"""Read-only graph neighborhood export for product UI."""

from __future__ import annotations

from typing import Any

from continuum.hydradb import HydraDBClient

NEIGHBORHOOD = """
MATCH (anchor {key: $entity_key})
OPTIONAL MATCH (c:Claim {object_id: $entity_key})
OPTIONAL MATCH (c)-[:SOURCED_FROM]->(a:Artifact)-[:FROM]->(s:Source)
OPTIONAL MATCH (c)-[:ABOUT]->(subj)
RETURN anchor.key AS anchor_key, labels(anchor)[0] AS anchor_label, anchor.name AS anchor_name,
       c.key AS claim_id, c.predicate AS predicate,
       c.subject_id AS subject_id, c.subject_name AS subject_name,
       a.key AS artifact_id, a.dsid AS artifact_dsid, a.kind AS artifact_kind,
       s.key AS source_id, s.name AS source_name,
       subj.key AS about_key, subj.name AS about_name, labels(subj)[0] AS about_label
"""


def export_entity_graph(
    client: HydraDBClient,
    entity_key: str,
    *,
    depth: int = 2,
) -> dict[str, Any]:
    """Export a read-only entity neighborhood for visualization."""
    _ = depth  # reserved for future hop expansion
    rows = client.execute(NEIGHBORHOOD, {"entity_key": entity_key}).rows
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def add_node(node_id: str, *, label: str, name: str, ntype: str, extra: dict | None = None) -> None:
        if node_id in nodes:
            return
        payload = {"id": node_id, "label": label, "name": name, "type": ntype}
        if extra:
            payload.update(extra)
        nodes[node_id] = payload

    if not rows and entity_key:
        add_node(entity_key, label=entity_key.split(":")[0], name=entity_key, ntype="entity")

    for row in rows:
        anchor_key = row.get("anchor_key") or entity_key
        if anchor_key:
            add_node(
                anchor_key,
                label=str(row.get("anchor_label") or "Entity"),
                name=str(row.get("anchor_name") or anchor_key),
                ntype="entity",
            )

        subject_id = row.get("subject_id")
        if subject_id:
            add_node(
                str(subject_id),
                label="Person",
                name=str(row.get("subject_name") or subject_id),
                ntype="person",
            )
            edge_key = (str(subject_id), anchor_key, str(row.get("predicate") or "OWNS"))
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append(
                    {
                        "source": edge_key[0],
                        "target": edge_key[1],
                        "predicate": edge_key[2],
                        "claim_id": row.get("claim_id"),
                    }
                )

        artifact_id = row.get("artifact_id")
        if artifact_id:
            source_name = str(row.get("source_name") or "source").lower()
            add_node(
                str(artifact_id),
                label="Artifact",
                name=str(row.get("artifact_kind") or artifact_id),
                ntype="artifact",
                extra={"source": source_name, "dsid": row.get("artifact_dsid")},
            )
            claim_id = row.get("claim_id")
            if claim_id:
                edge_key = (str(claim_id), str(artifact_id), "SOURCED_FROM")
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({"source": edge_key[0], "target": edge_key[1], "predicate": "SOURCED_FROM"})

        source_id = row.get("source_id")
        if source_id and artifact_id:
            add_node(
                str(source_id),
                label="Source",
                name=str(row.get("source_name") or source_id),
                ntype="source",
            )
            edge_key = (str(artifact_id), str(source_id), "FROM")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({"source": edge_key[0], "target": edge_key[1], "predicate": "FROM"})

        about_key = row.get("about_key")
        if about_key:
            add_node(
                str(about_key),
                label=str(row.get("about_label") or "Entity"),
                name=str(row.get("about_name") or about_key),
                ntype="entity",
            )

    return {
        "entity": entity_key,
        "nodes": list(nodes.values()),
        "edges": edges,
    }
