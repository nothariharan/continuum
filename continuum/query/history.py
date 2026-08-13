from __future__ import annotations

from continuum.hydradb import HydraDBClient
from ._helpers import absent


def owner_on(client: HydraDBClient, account_id: str, date: str) -> dict:
    rows = client.execute(
        "MATCH (p:Person)-[r:OWNS]->(a:Account {key: $account_id}) "
        "WHERE r.valid_from <= $date AND r.valid_to > $date "
        "RETURN p.key AS person_id, p.name AS person_name, r.valid_from AS valid_from, r.valid_to AS valid_to "
        "ORDER BY r.valid_from DESC LIMIT 1",
        {"account_id": account_id, "date": date},
    ).rows
    if not rows:
        return absent(account_id, "OWNS")
    value = rows[0]
    return {
        "status": "definitive",
        "entity_id": account_id,
        "predicate": "OWNS",
        "as_of": date,
        "value": {"entity_id": value["person_id"], "name": value["person_name"]},
        "valid_from": value["valid_from"],
        "valid_to": value["valid_to"],
        "confidence": 0.96,
        "evidence": [],
    }
