"""B4 regression tests — hermetic HydraDB lifecycle (PR #10 review).

The review showed the E2E outcome depended on database history: leftover
claims about the same entities (at other id ranges) silently changed
answers (7/20 polluted vs 9/20 clean). These tests prove the vertical is
independent of prior state.

Lock:
- polluted graph -> same answers as clean graph
- repeated runs -> identical claims, entities, answers
- a failed cleanup fails loudly instead of running a dirty graph
"""

from __future__ import annotations

from pathlib import Path

import pytest

from continuum.hydradb import HydraDBClient
from continuum.hydradb.health import diagnose
from continuum.pipeline.source_e2e import SourceE2EPipeline, wipe_for_entities

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "data" / "ground_truth" / "source-e2e-v1"


def _hydra_available() -> bool:
    try:
        return diagnose().queryable
    except Exception:
        return False


pytestmark_hydradb = pytest.mark.skipif(not _hydra_available(), reason="HydraDB not running")

SEED_JUNK = """
UNWIND $rows AS row
MERGE (c {id: row.id})
SET c:Claim,
    c.key = row.key,
    c.artifact_id = row.artifact_id,
    c.subject_mention = row.subject_mention,
    c.subject_id = row.subject_id,
    c.subject_name = row.subject_name,
    c.object_id = row.object_id,
    c.predicate = row.predicate,
    c.observed_at = row.observed_at,
    c.valid_from = row.valid_from,
    c.valid_to = row.valid_to
"""


def _seed_junk(client: HydraDBClient) -> None:
    """Claims at LOW ids (outside the phase2b reset range) referencing the
    same entities with LATER validity — the exact pollution shape that
    previously flipped the answers."""
    rows = [
        {
            "id": 20,
            "key": "claim:junk-owner-gmail",
            "artifact_id": "dsid_00000000000000000000000000000001",
            "subject_mention": "Intruder X",
            "subject_id": "person:intruder",
            "subject_name": "Intruder X",
            "object_id": "account:acme",
            "predicate": "OWNS",
            "observed_at": "2026-12-31",
            "valid_from": "2026-12-31",
            "valid_to": "9999-12-31",
        },
        {
            "id": 21,
            "key": "claim:junk-owner-slack",
            "artifact_id": "dsid_00000000000000000000000000000002",
            "subject_mention": "Intruder Y",
            "subject_id": "person:intruder-y",
            "subject_name": "Intruder Y",
            "object_id": "account:cedarbank",
            "predicate": "OWNS",
            "observed_at": "2026-12-31",
            "valid_from": "2026-12-31",
            "valid_to": "9999-12-31",
        },
    ]
    client.execute_batch(SEED_JUNK, rows)


def _answer_signature(result) -> list[tuple]:
    return [
        (r["question_id"], r["got"], r["status"])
        for r in result.question_results
    ]


@pytest.mark.hydradb
@pytestmark_hydradb
def test_source_e2e_hermetic_against_pollution(client: HydraDBClient):
    _seed_junk(client)
    pipeline = SourceE2EPipeline(GOLD, refinement_provider="mock")
    polluted = pipeline.run(client, load_graph=True)

    clean = pipeline.run(client, load_graph=True)

    for row in polluted.question_results:
        assert "Intruder" not in row["got"], (
            f"{row['question_id']} answered from leftover state: {row['got']!r}"
        )
    assert _answer_signature(polluted) == _answer_signature(clean)
    assert len(polluted.loadable_claims) == len(clean.loadable_claims)


@pytest.mark.hydradb
@pytestmark_hydradb
def test_source_e2e_repeated_runs_deterministic(client: HydraDBClient):
    pipeline = SourceE2EPipeline(GOLD, refinement_provider="mock")
    first = pipeline.run(client, load_graph=True)
    second = pipeline.run(client, load_graph=True)

    def claim_sig(result):
        return sorted(
            (c["claim_id"], c["subject_mention"], c["predicate"], c["object_mention"])
            for c in result.loadable_claims
        )

    assert claim_sig(first) == claim_sig(second)
    assert _answer_signature(first) == _answer_signature(second)
    assert first.extraction_metrics["precision"] == second.extraction_metrics["precision"]
    assert first.extraction_metrics["recall"] == second.extraction_metrics["recall"]


@pytest.mark.hydradb
@pytestmark_hydradb
def test_source_e2e_wipe_fails_loudly_on_leftovers(client: HydraDBClient):
    _seed_junk(client)
    resolutions = {
        "account:acme": {"name": "Acme", "label": "Account", "mentions": ["Acme"], "aliases": []},
    }
    wipe_for_entities(client, resolutions)
    rows = client.execute(
        "MATCH (c:Claim {object_id: 'account:acme'}) RETURN count(*) AS n"
    ).rows
    assert rows[0]["n"] == 0
