"""Seed the small deterministic Phase 1 company fixture into real HydraDB."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuum.hydradb import HydraDBClient
from continuum.hydradb.artifacts import delete_all_artifacts

OPEN_END = "9999-12-31"
FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "company.json"


def seed(reset: bool = False) -> dict[str, int]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    all_records = fixture["people"] + fixture["projects"] + fixture["accounts"] + fixture["sources"] + fixture["artifacts"] + fixture["claims"]
    graph_ids = {record["id"]: index for index, record in enumerate(all_records, start=1)}
    with HydraDBClient() as client:
        if reset:
            for label in ("Person", "Project", "Account", "Source", "Claim"):
                client.execute(f"MATCH (n:{label}) DETACH DELETE n")
            delete_all_artifacts(client)

        node_groups = {
            "Person": fixture["people"],
            "Project": fixture["projects"],
            "Account": fixture["accounts"],
            "Source": fixture["sources"],
        }
        for label, rows in node_groups.items():
            node_rows = [{**row, "id": graph_ids[row["id"]], "key": row["id"]} for row in rows]
            client.execute_batch(
                f"UNWIND $rows AS row MERGE (n {{id: row.id}}) SET n:{label}, n.key = row.key, n.name = row.name",
                node_rows,
            )
        people_aliases = [{"id": graph_ids[row["id"]], "aliases": "|".join(row.get("aliases", []))} for row in fixture["people"]]
        for row in people_aliases:
            client.execute(
                "MATCH (n:Person {id: $id}) SET n.aliases = $aliases",
                row,
            )
        artifact_rows = [{**row, "id": graph_ids[row["id"]], "key": row["id"]} for row in fixture["artifacts"]]
        client.execute_batch(
            "UNWIND $rows AS row MERGE (n {id: row.id}) "
            "SET n:Artifact, n.key = row.key, n.kind = row.kind, n.observed_at = row.observed_at, n.content = row.content",
            artifact_rows,
        )
        claims = []
        people_by_id = {row["id"]: row["name"] for row in fixture["people"]}
        for claim in fixture["claims"]:
            claims.append({**claim, "id": graph_ids[claim["id"]], "key": claim["id"], "subject_name": people_by_id[claim["subject_id"]], "valid_to": claim["valid_to"] or OPEN_END})
        client.execute_batch(
            "UNWIND $rows AS row MERGE (n {id: row.id}) SET n:Claim, "
            "n.key = row.key, n.subject_id = row.subject_id, n.predicate = row.predicate, "
            "n.subject_name = row.subject_name, "
            "n.object_id = row.object_id, n.observed_at = row.observed_at, "
            "n.valid_from = row.valid_from, n.valid_to = row.valid_to",
            claims,
        )
        def create_relationship(rel_type: str, source_label: str, target_label: str, rows: list[dict]) -> None:
            client.execute_batch(
                f"UNWIND $rows AS row MATCH (s:{source_label} {{id: row.source}}), (d:{target_label} {{id: row.target}}) "
                f"CREATE (s)-[:{rel_type}]->(d)",
                rows,
            )
        create_relationship("FROM", "Artifact", "Source", [{"source": graph_ids[r["id"]], "target": graph_ids[r["source_id"]]} for r in fixture["artifacts"]])
        create_relationship("SOURCED_FROM", "Claim", "Artifact", [{"source": graph_ids[r["id"]], "target": graph_ids[r["artifact_id"]]} for r in fixture["claims"]])
        for target_label in ("Account", "Project"):
            create_relationship(
                "ABOUT", "Claim", target_label,
                [{"source": graph_ids[r["id"]], "target": graph_ids[r["object_id"]]} for r in fixture["claims"] if r["object_id"].startswith(target_label.lower() + ":")],
            )
        create_relationship(
            "CONTRADICTS", "Claim", "Claim",
            [{"source": graph_ids["claim:arjun-acme-gmail"], "target": graph_ids[claim_id]} for claim_id in ("claim:sarah-acme-linear", "claim:sarah-acme-slack")],
        )
        ownership = [
            {"source": graph_ids[c["subject_id"]], "target": graph_ids[c["object_id"]], "valid_from": c["valid_from"], "valid_to": c["valid_to"] or OPEN_END}
            for c in fixture["claims"] if c["predicate"] == "OWNS"
        ]
        for target_label in ("Account", "Project"):
            create_relationship(
                "OWNS", "Person", target_label,
                [row for row, claim in zip(ownership, [c for c in fixture["claims"] if c["predicate"] == "OWNS"]) if claim["object_id"].startswith(target_label.lower() + ":")],
            )
        for row in ownership:
            client.execute(
                "MATCH (s:Person {id: $source})-[r:OWNS]->(d {id: $target}) "
                "SET r.valid_from = $valid_from, r.valid_to = $valid_to",
                row,
            )
    return {"people": len(fixture["people"]), "accounts": len(fixture["accounts"]), "projects": len(fixture["projects"]), "artifacts": len(fixture["artifacts"]), "claims": len(fixture["claims"]), "relationships": len(fixture["artifacts"]) + len(fixture["claims"]) * 2 + len(ownership)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    print("Synthetic company loaded")
    print(json.dumps(seed(reset=args.reset), indent=2))
