"""Versioned benchmark scorer tests (Batch 6.1)."""

from __future__ import annotations

from continuum.eval.benchmark.scoring import score_answer_v1, score_answer_v2


def test_v2_empty_answer_never_passes():
    assert score_answer_v2("", "Priya Nair") is False
    assert score_answer_v2("   ", "Priya Nair") is False
    assert score_answer_v2("", "") is False


def test_v1_empty_answer_passes_due_to_bug():
    # Documents the legacy bug that v2 fixes.
    assert score_answer_v1("", "Priya Nair") is True


def test_v2_one_char_answer_never_passes():
    assert score_answer_v2("x", "Priya Nair") is False
    assert score_answer_v2("x", "x") is False


def test_v2_exact_match():
    assert score_answer_v2("Priya Nair", "Priya Nair") is True


def test_v2_substring_both_directions():
    assert score_answer_v2("the owner is Priya Nair", "Priya Nair") is True
    assert score_answer_v2("Priya Nair", "the owner is Priya Nair") is True


def test_v2_abstention_symmetry():
    assert score_answer_v2("unknown - abstain", "not found in the documents") is True
    assert score_answer_v2("cannot determine", "no information available") is True


def test_v2_token_overlap():
    assert score_answer_v2("the default limits are 10 MiB per file", "the default limit is 10 MiB per file") is True


def test_v2_mismatch_false():
    assert score_answer_v2("Morgan", "Priya Nair") is False


def test_golden_v1_v2_flips():
    """Cases that flip from v1 (True) to v2 (False) — the documented delta."""
    flips = [
        ("", "Priya Nair"),
        ("   ", "anything at all"),
        ("a", "Acme Corp"),  # 1-char got is a substring of gold in v1
    ]
    for got, gold in flips:
        assert score_answer_v1(got, gold) is True
        assert score_answer_v2(got, gold) is False
