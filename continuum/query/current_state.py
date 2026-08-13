from __future__ import annotations

from continuum.hydradb import HydraDBClient
from ._helpers import absent


def current_owner(client: HydraDBClient, account_id: str) -> dict:
    row = client.execute(
        "MATCH (p:Person)-[r:OWNS]->(a:Account {key: $account_id}) "
        "WHERE r.valid_to = $open_end "
        "RETURN p.key AS person_id, p.name AS person_name, r.valid_from AS valid_from "
        "ORDER BY r.valid_from DESC LIMIT 1",
        {"account_id": account_id, "open_end": "9999-12-31"},
    ).rows
    if not row:
        return absent(account_id, "OWNS")
    value = row[0]
    return {
        "status": "definitive",
        "entity_id": account_id,
        "predicate": "OWNS",
        "value": {"entity_id": value["person_id"], "name": value["person_name"]},
        "valid_from": value["valid_from"],
        "valid_to": None,
        "confidence": 0.96,
        "evidence": [],
    }
