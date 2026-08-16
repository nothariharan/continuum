"""Phase 3B real-identity validation tests — teammate data consumption."""

from __future__ import annotations

from continuum.entities.eval import EntityResolutionEval
from continuum.entities.pairs import load_teammate_identity_pairs
from continuum.entities.resolver import EntityResolver

REAL_PAIRS = "data/entity_resolution/v1/identity-pairs.jsonl"


def test_teammate_pairs_load_through_contract():
    pairs = load_teammate_identity_pairs(REAL_PAIRS)
    assert len(pairs) == 103


def test_teammate_pairs_label_distribution():
    from collections import Counter

    pairs = load_teammate_identity_pairs(REAL_PAIRS)
    counts = Counter(p.label for p in pairs)
    assert counts == {"SAME_ENTITY": 27, "DIFFERENT_ENTITY": 25, "UNCERTAIN": 51}


def test_teammate_feature_coverage():
    pairs = load_teammate_identity_pairs(REAL_PAIRS)
    covered = sum(1 for p in pairs if p.features.get("email_match") is not None)
    assert covered > 0, "email_match must be present on some pairs"
    # name_similarity is the most covered feature
    covered_name = sum(1 for p in pairs if p.features.get("name_similarity") is not None)
    assert covered_name == len(pairs), "name_similarity expected on every pair"


def test_real_baseline_zero_false_merges():
    pairs = load_teammate_identity_pairs(REAL_PAIRS)
    report = EntityResolutionEval(pairs).run(EntityResolver())
    assert report["metrics"]["false_merge_rate"] == 0.0
    assert report["metrics"]["same_precision"] == 1.0
    assert report["metrics"]["pair_accuracy"] >= 0.85


def test_cross_org_email_never_merges():
    from continuum.entities import ResolutionDecision
    from continuum.entities.candidates import candidate_from_mention

    resolver = EntityResolver()
    a = candidate_from_mention("David Park", emails=["david.park@redwood.com"])
    b = candidate_from_mention("David Park", emails=["david.park@acme.com"])
    verdict = resolver.resolve_pair(a, b)
    assert verdict.decision != ResolutionDecision.MERGE


def test_role_mailbox_stays_separate():
    from continuum.entities import ResolutionDecision
    from continuum.entities.candidates import candidate_from_mention

    resolver = EntityResolver()
    a = candidate_from_mention("procurement@acme.ai", emails=["procurement@acme.ai"])
    b = candidate_from_mention("procurement@redwood.com", emails=["procurement@redwood.com"])
    verdict = resolver.resolve_pair(a, b)
    assert verdict.decision == ResolutionDecision.KEEP_SEPARATE
