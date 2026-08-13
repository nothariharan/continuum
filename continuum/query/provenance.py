from __future__ import annotations

from continuum.hydradb import HydraDBClient
from ._helpers import absent


def ownership_provenance(client: HydraDBClient, account_id: str) -> dict:
    rows = client.execute(
        "MATCH (c:Claim {object_id: $account_id})-[:ABOUT]->(a:Account {key: $account_id}), "
        "(c)-[:SOURCED_FROM]->(artifact:Artifact)-[:FROM]->(source:Source) "
        "WHERE c.predicate = 'OWNS' "
        "RETURN c.subject_id AS person_id, c.subject_name AS person_name, c.key AS claim_id, "
        "artifact.key AS artifact_id, artifact.kind AS artifact_kind, "
        "artifact.observed_at AS observed_at, source.key AS source_id, source.name AS source_name "
        "ORDER BY observed_at",
        {"account_id": account_id},
    ).rows
    if not rows:
        return absent(account_id, "OWNS")
    return {
        "status": "definitive",
        "entity_id": account_id,
        "predicate": "OWNS",
        "value": {"entity_id": rows[-1]["person_id"], "name": rows[-1]["person_name"]},
        "evidence": [
            {
                "claim_id": row["claim_id"],
                "artifact_id": row["artifact_id"],
                "artifact_kind": row["artifact_kind"],
                "source_id": row["source_id"],
                "source": row["source_name"],
                "observed_at": row["observed_at"],
            }
            for row in rows
        ],
    }
