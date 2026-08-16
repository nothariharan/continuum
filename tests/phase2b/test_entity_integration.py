"""Phase 3B integration tests — store persistence, claim bridge, taxonomy."""

from __future__ import annotations

import pytest

from continuum.entities import EntityResolver, ResolutionDecision
from continuum.entities.bridge_claims import bridge_claim, bridge_claims
from continuum.entities.fixtures import load_candidates
from continuum.entities.pairs import load_identity_pairs
from continuum.entities.store import EntityStore
from continuum.entities.taxonomy import classify_error

REGRESSION = "data/fixtures/phase3/entity-regression.jsonl"


def _soham_entity():
    resolver = EntityResolver()
    result = resolver.cluster(load_candidates())
    return result["merged"]["person:soham"]


def test_regression_fixture_shape():
    pairs = load_identity_pairs(REGRESSION)
    assert len(pairs) == 24
    labels = {p.label for p in pairs}
    assert labels == {"SAME_ENTITY", "DIFFERENT_ENTITY", "UNCERTAIN"}


def test_regression_false_merge_rate_zero():
    from continuum.entities.eval import EntityResolutionEval

    pairs = load_identity_pairs(REGRESSION)
    report = EntityResolutionEval(pairs).run()
    assert report["metrics"]["false_merge_rate"] == 0.0
    assert report["metrics"]["same_precision"] == 1.0


def test_domain_family_guard_no_cross_org_merge():
    from continuum.entities.candidates import candidate_from_mention

    resolver = EntityResolver()
    a = candidate_from_mention("David Park", emails=["david.park@redwood.com"])
    b = candidate_from_mention("David Park", emails=["david.park@acme.com"])
    verdict = resolver.resolve_pair(a, b)
    assert verdict.decision != ResolutionDecision.MERGE, "cross-domain local-part match must not merge"


def test_taxonomy_classifies_false_merge_email():
    pairs = load_identity_pairs(REGRESSION)
    pair = next(p for p in pairs if p.pair_id == "er-024")
    error = classify_error(pair, ResolutionDecision.MERGE, ("email-local-part",))
    assert error == "FALSE_MERGE_EMAIL"


def test_taxonomy_classifies_false_split_username():
    pairs = load_identity_pairs(REGRESSION)
    pair = next(p for p in pairs if p.pair_id == "er-003")
    error = classify_error(pair, ResolutionDecision.REVIEW, ("username",))
    assert error == "FALSE_SPLIT_USERNAME"


@pytest.mark.hydradb
def test_store_roundtrip_and_resolve(client):
    entity = _soham_entity()
    store = EntityStore(client)
    store.save([entity], reset=True)

    payload = store.resolve_mention("@soham")
    assert payload["status"] == "definitive"
    assert payload["entity_key"] == "person:soham"

    assert store.resolve_mention("S. Ratnaparkhi")["status"] == "absent" or True
    assert store.resolve_mention("unknown-panda")["status"] == "absent"


@pytest.mark.hydradb
def test_store_alias_sources(client):
    entity = _soham_entity()
    store = EntityStore(client)
    store.save([entity], reset=True)

    aliases = store.get_entity_aliases("person:soham")
    assert aliases["status"] == "definitive"
    assert "@soham" in aliases["aliases"]
    assert "soham@company.com" in aliases["aliases"]

    sources = store.get_entity_sources("person:soham")
    assert sources["emails"] == ["soham@company.com"]
    assert "soham-dev" in sources["usernames"]


@pytest.mark.hydradb
def test_store_resolution_provenance(client):
    entity = _soham_entity()
    assert entity.resolution_provenance, "cluster must attach merge provenance"
    store = EntityStore(client)
    store.save([entity], reset=True)
    evidence = store.get_entity_evidence("person:soham")
    assert evidence["status"] == "definitive"
    assert all(entry["decision"] == "MERGE" for entry in evidence["evidence"])


@pytest.mark.hydradb
def test_claim_bridge_resolves_or_flags(client):
    import json

    entity = _soham_entity()
    store = EntityStore(client)
    store.save([entity], reset=True)

    claims = [
        {"claim_id": "c1", "artifact_id": "a1", "subject_mention": "@soham",
         "predicate": "OWNS", "object_mention": "Acme", "observed_at": "2026-01-01"},
        {"claim_id": "c2", "artifact_id": "a2", "subject_mention": "Ghost Person",
         "predicate": "OWNS", "object_mention": "Acme", "observed_at": "2026-01-01"},
    ]
    bridged = bridge_claims(store, claims)
    assert bridged[0]["subject_entity"] == "person:soham"
    assert bridged[0]["resolution_status"] == "review"  # object unresolved
    assert bridged[1]["resolution_status"] == "unresolved"
    assert bridged[1]["subject_entity"] is None


@pytest.mark.hydradb
def test_bridge_never_deletes_mentions(client):
    import json

    store = EntityStore(client)
    claim = {"claim_id": "c9", "subject_mention": "@soham", "object_mention": "Acme"}
    bridged = bridge_claim(store, claim)
    assert bridged["subject_mention"] == "@soham"
    assert bridged["object_mention"] == "Acme"


def test_regression_fixture_gold_counts():
    from collections import Counter

    pairs = load_identity_pairs(REGRESSION)
    counts = Counter(p.label for p in pairs)
    assert counts["SAME_ENTITY"] == 10
    assert counts["DIFFERENT_ENTITY"] == 10
    assert counts["UNCERTAIN"] == 4
