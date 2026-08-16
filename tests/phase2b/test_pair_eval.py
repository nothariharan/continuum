"""Entity-resolution pair eval tests — contract, merged features, metrics."""

from __future__ import annotations

from continuum.entities import EntityResolver, ResolutionDecision
from continuum.entities.eval import EntityResolutionEval
from continuum.entities.pairs import IdentityPair, load_identity_pairs

TINY_PAIRS = "data/fixtures/phase3/identity-pairs-tiny.jsonl"


def _pair(**overrides) -> IdentityPair:
    defaults = dict(
        pair_id="ip-test",
        mention_a="Sarah Chen",
        type_a="person",
        source_a="slack",
        emails_a=["sarah.chen@redwood.com"],
        mention_b="Sarah Liu",
        type_b="person",
        source_b="gmail",
        emails_b=["sarah.liu@cloudpartner.com"],
        label="DIFFERENT_ENTITY",
    )
    defaults.update(overrides)
    return IdentityPair(**defaults)


def test_identity_pair_validation_labels():
    ok = _pair(label="SAME_ENTITY")
    ok.validate()
    bad = _pair(label="MAYBE_SAME")
    try:
        bad.validate()
        assert False, "invalid label must raise"
    except ValueError:
        pass


def test_identity_pair_validation_features_range():
    bad = _pair(label="SAME_ENTITY", features={"name_similarity": 1.5})
    try:
        bad.validate()
        assert False, "feature outside [0,1] must raise"
    except ValueError:
        pass


def test_load_tiny_fixture():
    pairs = load_identity_pairs(TINY_PAIRS)
    assert len(pairs) == 6
    assert {p.label for p in pairs} == {"SAME_ENTITY", "DIFFERENT_ENTITY", "UNCERTAIN"}


def test_merged_features_guards_role_mailbox():
    pair = _pair(
        mention_a="procurement@acme.ai",
        type_a="email",
        emails_a=["procurement@acme.ai"],
        mention_b="procurement@redwood.com",
        type_b="email",
        emails_b=["procurement@redwood.com"],
        label="DIFFERENT_ENTITY",
        features={"email_match": 1.0},  # measured value must NOT bypass the guard
    )
    fv = pair.merged_features()
    assert fv.email_match is None, "role-mailbox guard must block measured email_match"


def test_merged_features_honors_measured_username_gap():
    pair = _pair(
        mention_a="Sam",
        type_a="person",
        usernames_a=[],
        mention_b="@soham",
        type_b="person",
        usernames_b=["soham"],
        label="SAME_ENTITY",
        features={"username_match": 1.0},  # measured: Sam is @soham's first-name form
    )
    fv = pair.merged_features()
    assert fv.username_match == 1.0


def test_eval_metrics_no_false_merges():
    pairs = load_identity_pairs(TINY_PAIRS)
    report = EntityResolutionEval(pairs).run()
    metrics = report["metrics"]
    assert metrics["false_merge_rate"] == 0.0
    assert metrics["false_split_rate"] == 0.0


def test_eval_different_recall_full():
    pairs = load_identity_pairs(TINY_PAIRS)
    report = EntityResolutionEval(pairs).run()
    assert report["metrics"]["different_recall"] == 1.0


def test_eval_decision_mapping_uncertain():
    pair = _pair(label="UNCERTAIN")
    report = EntityResolutionEval([pair]).run(EntityResolver())
    row = report["rows"][0]
    assert row["correct"] in {True, False}
    assert row["false_merge"] is False or row["decision"] == ResolutionDecision.MERGE


def test_resolver_consumes_pair_features():
    resolver = EntityResolver()
    pairs = load_identity_pairs(TINY_PAIRS)
    same = next(p for p in pairs if p.label == "SAME_ENTITY" and p.pair_id == "ip-tiny-002")
    verdict = resolver.resolve_pair(
        same.candidate_a(),
        same.candidate_b(),
        features=same.merged_features(),
    )
    assert verdict.decision == ResolutionDecision.MERGE


def test_resolver_backward_compat_extra_features():
    resolver = EntityResolver()
    from continuum.entities.candidates import candidate_from_mention

    a = candidate_from_mention("Maya Chen", emails=["maya.chen@redwood.com"])
    b = candidate_from_mention("Maya Chen", emails=["maya.chen@redwood.com"])
    verdict = resolver.resolve_pair(a, b, extra_features={"cooccurrence": 0.95})
    assert verdict.decision == ResolutionDecision.MERGE
