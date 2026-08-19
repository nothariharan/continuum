"""Batch 5 — entity-resolution hardening (identity convergence + safe non-merge).

The critical invariant is a ZERO false-merge rate: a wrong merge corrupts the
whole company graph, so same-name-different-org pairs must never MERGE. The
positive convergence set must merge on strong signals (email, external id,
email↔username).
"""

from __future__ import annotations

from pathlib import Path

from continuum.entities.eval import evaluate_pairs
from continuum.entities.models import ResolutionDecision
from continuum.entities.pairs import load_identity_pairs
from continuum.pipeline.source_e2e import _person_entity_key

ROOT = Path(__file__).resolve().parents[2]
HARD = ROOT / "data" / "fixtures" / "phase3" / "identity-pairs-hard.jsonl"


def _report() -> dict:
    pairs = load_identity_pairs(HARD)
    return evaluate_pairs(pairs)


def test_zero_false_merge_on_negatives():
    report = _report()
    assert report["metrics"]["false_merge_count"] == 0
    assert report["metrics"]["false_merge_rate"] == 0.0
    # No DIFFERENT_ENTITY pair may ever be merged.
    for row in report["rows"]:
        if row["gold"] == "DIFFERENT_ENTITY":
            assert row["decision"] != ResolutionDecision.MERGE.value, row


def test_positive_convergence_merges_on_strong_signals():
    report = _report()
    assert report["metrics"]["same_precision"] == 1.0
    assert report["metrics"]["same_recall"] >= 0.99  # every SAME pair merges
    same_rows = [r for r in report["rows"] if r["gold"] == "SAME_ENTITY"]
    assert same_rows and all(r["decision"] == "MERGE" for r in same_rows)


def test_uncertain_pair_never_merges():
    report = _report()
    for row in report["rows"]:
        if row["gold"] == "UNCERTAIN":
            assert row["decision"] in {"REVIEW", "ABSTAIN"}, row


def test_key_derivation_priority_email_over_username_over_slug():
    # email local-part > username > name-slug (feeds cross-source convergence)
    assert _person_entity_key("Priya Nair", email="priya.nair@company.com", username="@priya") == "person:priya-nair"
    assert _person_entity_key("Priya Nair", username="@priya.nair") == "person:priya-nair"
    assert _person_entity_key("Priya Nair") == "person:priya-nair"
