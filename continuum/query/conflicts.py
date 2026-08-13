from __future__ import annotations

from continuum.hydradb import HydraDBClient


def find_conflicts(client: HydraDBClient, account_id: str) -> dict:
    rows = client.execute(
        "MATCH (c:Claim {object_id: $account_id})-[:ABOUT]->(a:Account {key: $account_id}) "
        "WHERE c.predicate = 'OWNS' "
        "RETURN c.key AS claim_id, c.subject_id AS subject_id, c.subject_name AS subject_name, "
        "c.observed_at AS observed_at, c.valid_from AS valid_from, c.valid_to AS valid_to "
        "ORDER BY c.observed_at",
        {"account_id": account_id},
    ).rows
    subjects = sorted({row["subject_id"] for row in rows})
    return {
        "status": "CONFLICT" if len(subjects) > 1 else "CONSISTENT",
        "entity_id": account_id,
        "predicate": "OWNS",
        "conflicting_subjects": subjects,
        "claims": rows,
    }
