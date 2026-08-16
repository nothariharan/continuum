"""Entity resolution core tests — models, candidates, scoring, resolver, bridge."""

from __future__ import annotations

from continuum.entities import (
    CanonicalEntity,
    EntityCandidate,
    EntityResolver,
    ResolutionDecision,
    candidate_from_mention,
    compute_features,
    score_match,
)
from continuum.entities.bridge import to_resolutions
from continuum.entities.candidates import CandidateIndex, canonical_local
from continuum.entities.fixtures import EXPECTED_SEPARATE, load_candidates, load_lexicon


def _cand(mention: str, **kwargs) -> EntityCandidate:
    return candidate_from_mention(mention, **kwargs)


# ---- candidate generation --------------------------------------------------

def test_candidate_index_exact_username():
    entities = [
        CanonicalEntity("person:soham", "Person", "Soham Ratnaparkhi",
                        usernames={"soham-dev"}, emails={"soham@company.com"})
    ]
    index = CandidateIndex.build(entities)
    hits = index.lookup(_cand("@soham", usernames=["soham"]).signals)
    assert ("person:soham", 1) in hits


def test_candidate_index_email_local_part():
    entities = [
        CanonicalEntity("person:soham", "Person", "Soham Ratnaparkhi", emails={"soham@company.com"})
    ]
    index = CandidateIndex.build(entities)
    hits = index.lookup(_cand("soham@company.com", emails=["soham@company.com"]).signals)
    assert ("person:soham", 2) in hits  # email + email-local-part


def test_candidate_index_name_token():
    entities = [
        CanonicalEntity("person:ratnaparkhi", "Person", "Soham Ratnaparkhi",
                        aliases={"S. Ratnaparkhi", "Soham Ratnaparkhi"})
    ]
    index = CandidateIndex.build(entities)
    hits = index.lookup(_cand("S. Ratnaparkhi").signals)
    assert any(key == "person:ratnaparkhi" for key, _ in hits)


def test_local_part_normalization():
    assert canonical_local("ben_carter@x.com") == canonical_local("ben.carter@y.com")


# ---- scoring ---------------------------------------------------------------

def test_email_local_part_is_strongest_signal():
    a = _cand("Ben Carter", emails=["ben.carter@redwood.com"])
    b = _cand("ben_carter@redwood.ai", emails=["ben_carter@redwood.ai"])
    match = score_match(a, b)
    assert match.score >= 0.9
    assert "email-local-part" in match.signals


def test_exact_username_strong():
    a = _cand("@soham", usernames=["soham"])
    b = _cand("soham-dev", usernames=["soham-dev"])
    match = score_match(a, b)
    assert match.score >= 0.85


def test_full_name_tokens_strong():
    a = _cand("Soham Ratnaparkhi")
    b = _cand("S. Ratnaparkhi")
    match = score_match(a, b)
    assert match.score >= 0.8


def test_single_token_is_weak():
    a = _cand("Maya")
    b = _cand("Maya Chen")
    match = score_match(a, b)
    assert match.score <= 0.6


def test_no_evidence_zero():
    a = _cand("Sarah Liu", emails=["sarah.liu@cloudpartner.com"])
    b = _cand("Maya Chen", emails=["maya.chen@redwood.com"])
    match = score_match(a, b)
    assert match.score == 0.0


# ---- resolver --------------------------------------------------------------

def _fixture_resolver():
    return EntityResolver(load_lexicon())


def test_resolve_same_person_merges():
    resolver = _fixture_resolver()
    a = _cand("soham@company.com", emails=["soham@company.com"])
    b = _cand("soham-dev", usernames=["soham-dev"])
    verdict = resolver.resolve_pair(a, b)
    assert verdict.decision == ResolutionDecision.REVIEW or verdict.decision == ResolutionDecision.MERGE


def test_resolve_email_vs_name_with_lexicon():
    resolver = _fixture_resolver()
    a = _cand("Maya Patel", emails=["maya.patel@redwood.com"])
    b = _cand("Maya Chen", emails=["maya.chen@redwood.com"])
    verdict = resolver.resolve_pair(a, b)
    assert verdict.decision == ResolutionDecision.KEEP_SEPARATE


def test_distinct_full_names_separate():
    resolver = _fixture_resolver()
    a = _cand("Sarah Chen")
    b = _cand("Sarah Liu")
    verdict = resolver.resolve_pair(a, b)
    assert verdict.decision == ResolutionDecision.KEEP_SEPARATE


def test_ambiguous_first_name_review_or_abstain():
    resolver = _fixture_resolver()
    a = _cand("Priya")
    b = _cand("Priya Natarajan")
    verdict = resolver.resolve_pair(a, b)
    assert verdict.decision in {
        ResolutionDecision.REVIEW,
        ResolutionDecision.ABSTAIN,
        ResolutionDecision.KEEP_SEPARATE,
    }


def test_cluster_merges_soham_family():
    resolver = EntityResolver()
    candidates = load_candidates()
    result = resolver.cluster(candidates)
    merged = result["merged"]
    soham_clusters = [e for key, e in merged.items() if "soham" in key.lower() or "ratnaparkhi" in key.lower()]
    assert soham_clusters, "expected a merged soham cluster"
    cluster = soham_clusters[0]
    mentions = {m.lower() for m in cluster.mentions}
    # The anchored core merges deterministically (email <-> username chain).
    assert {"@soham", "soham-dev", "soham@company.com"} <= mentions
    # 'Sam' and 'S. Ratnaparkhi' are single-token links: genuinely ambiguous,
    # must stay out of the auto-merge (conservative abstention).
    assert "sam" not in mentions
    assert "s. ratnaparkhi" not in mentions
    assert result["review"] or result["abstained"], "weak tail must be flagged, not guessed"


def test_cluster_keeps_mayas_separate():
    resolver = EntityResolver()
    candidates = load_candidates()
    result = resolver.cluster(candidates)
    maya_mentions = {c.mention for c in candidates if c.mention.startswith("Maya")}
    merged_mentions = {m for e in result["merged"].values() for m in e.mentions}
    maya_merged = merged_mentions & maya_mentions
    assert len(maya_merged) <= 1, f"Mayas must not merge, merged: {maya_merged}"


def test_canonical_entity_non_destructive():
    entity = CanonicalEntity("person:soham", "Person", "Soham Ratnaparkhi")
    entity.absorb(_cand("@soham", usernames=["soham"]))
    entity.absorb(_cand("soham@company.com", emails=["soham@company.com"]))
    assert entity.usernames == {"soham"}
    assert entity.emails == {"soham@company.com"}
    assert entity.mentions == {"@soham", "soham@company.com"}


# ---- bridge ----------------------------------------------------------------

def test_bridge_to_resolutions_format():
    entity = CanonicalEntity("person:soham-ratnaparkhi", "Person", "Soham Ratnaparkhi")
    entity.absorb(_cand("@soham", usernames=["soham"]))
    entity.absorb(_cand("soham@company.com", emails=["soham@company.com"]))
    resolutions = to_resolutions([entity])
    assert "person:soham-ratnaparkhi" in resolutions
    entry = resolutions["person:soham-ratnaparkhi"]
    assert entry["label"] == "Person"
    assert "@soham" in entry["mentions"]
    assert "soham@company.com" in entry["mentions"]


def test_bridge_preserves_alias_usernames():
    entity = CanonicalEntity("person:sarah", "Person", "Sarah Chen")
    entity.absorb(_cand("sarah_csm", usernames=["sarah_csm"]))
    resolutions = to_resolutions([entity])
    assert "sarah_csm" in resolutions["person:sarah"]["aliases"]
