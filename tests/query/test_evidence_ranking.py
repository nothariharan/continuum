"""Cross-source evidence ranking + grouping (Section 10) — pure unit tests."""

from __future__ import annotations

from continuum.query.evidence import (
    evidence_sources,
    group_evidence_by_subject,
    rank_evidence,
    summarize_cross_source,
)


def _ev(subject, source, kind, observed):
    return {
        "claim_id": f"{subject}-{source}",
        "subject_mention": subject,
        "subject_id": f"person:{subject.lower()}",
        "object_mention": "Acme",
        "artifact_kind": kind,
        "source": source,
        "observed_at": observed,
    }


def test_current_subject_evidence_ranks_first():
    ev = [
        _ev("Morgan", "Gmail", "gmail_message", "2026-07-01"),
        _ev("Priya", "Slack", "slack_message", "2026-08-01"),
    ]
    ranked = rank_evidence(ev, current_subject="Priya")
    assert ranked[0]["subject_mention"] == "Priya"


def test_recency_breaks_ties_within_same_subject():
    ev = [
        _ev("Priya", "Slack", "slack_message", "2026-07-01"),
        _ev("Priya", "Gmail", "gmail_message", "2026-08-01"),
    ]
    ranked = rank_evidence(ev, current_subject="Priya")
    assert ranked[0]["observed_at"] == "2026-08-01"


def test_formal_kind_breaks_ties_at_equal_recency():
    ev = [
        _ev("Priya", "Slack", "slack_message", "2026-08-01"),
        _ev("Priya", "Gmail", "gmail_message", "2026-08-01"),
    ]
    ranked = rank_evidence(ev, current_subject="Priya")
    # Same subject + same date -> the more formal record (email) leads.
    assert ranked[0]["source"] == "Gmail"


def test_no_fabricated_confidence():
    ev = [_ev("Priya", "Slack", "slack_message", "2026-08-01")]
    ranked = rank_evidence(ev, current_subject="Priya")
    assert "confidence" not in ranked[0]


def test_group_by_subject():
    ev = [
        _ev("Priya", "Slack", "slack_message", "2026-08-01"),
        _ev("Priya", "Gmail", "gmail_message", "2026-08-02"),
        _ev("Morgan", "Gmail", "gmail_message", "2026-07-01"),
    ]
    groups = group_evidence_by_subject(ev)
    assert set(groups) == {"Priya", "Morgan"}
    assert len(groups["Priya"]) == 2


def test_summarize_cross_source_flags_multi_source():
    ev = [
        _ev("Priya", "Slack", "slack_message", "2026-07-28"),
        _ev("Priya", "Gmail", "gmail_message", "2026-08-01"),
    ]
    summary = summarize_cross_source(ev, current_subject="Priya")
    assert summary["multi_source"] is True
    assert set(summary["sources"]) == {"Slack", "Gmail"}
    assert summary["top"]["source"] == "Gmail"  # most recent formal record


def test_single_source_not_multi():
    ev = [_ev("Priya", "Slack", "slack_message", "2026-08-01")]
    assert summarize_cross_source(ev)["multi_source"] is False
    assert evidence_sources(ev) == ["Slack"]
