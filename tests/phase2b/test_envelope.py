"""Canonical state-result envelope: every query returns the same key structure."""

from __future__ import annotations

import pytest

from continuum.query import (
    resolve_conflicts,
    resolve_provenance,
    resolve_state,
    resolve_state_on,
)
from continuum.query.result import ENVELOPE_KEYS, absent, result


def test_envelope_builder_has_all_keys():
    assert set(result("account:acme", "OWNS", "definitive").keys()) == ENVELOPE_KEYS
    assert set(absent("account:acme", "OWNS").keys()) == ENVELOPE_KEYS
    assert absent("account:acme", "OWNS")["value"] is None
    assert absent("account:acme", "OWNS")["evidence"] == []
    assert absent("account:acme", "OWNS")["status"] == "absent"


@pytest.mark.hydradb
def test_all_resolvers_return_identical_envelope(loaded_real_claims, client):
    operations = [
        resolve_state(client, "account:cedarbank", "OWNS"),
        resolve_state_on(client, "account:cedarbank", "2026-06-01", "OWNS"),
        resolve_conflicts(client, "account:cedarbank", "OWNS"),
        resolve_provenance(client, "account:cedarbank", "OWNS"),
        resolve_state(client, "account:orionai", "OWNS"),
    ]
    for payload in operations:
        assert set(payload.keys()) == ENVELOPE_KEYS, payload
    assert operations[2]["status"] == "conflict"
    assert operations[3]["status"] == "definitive"
    assert operations[4]["status"] == "absent"
    assert operations[4]["value"] is None
    for item in operations[3]["evidence"]:
        assert set(item.keys()) == {
            "claim_id",
            "subject_mention",
            "object_mention",
            "artifact_id",
            "artifact_kind",
            "source_id",
            "source",
            "observed_at",
        }
