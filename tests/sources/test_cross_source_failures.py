"""Cross-source ingestion failure taxonomy (Section 19)."""

from __future__ import annotations

import pytest

from continuum.sources.failures import (
    CROSS_SOURCE_FAILURES,
    classify_gmail_error,
    classify_state_status,
    empty_taxonomy,
    is_defect,
    merge_taxonomy,
)
from continuum.sources.gmail.live import GmailLiveError
from continuum.sources.gmail.oauth import GmailAuthError


def test_taxonomy_covers_required_categories():
    required = {
        "GMAIL_INGESTION_FAILURE", "GMAIL_AUTH_FAILURE", "GMAIL_PARSE_FAILURE",
        "CROSS_SOURCE_ER_FAILURE", "CROSS_SOURCE_TEMPORAL_FAILURE",
        "CROSS_SOURCE_CONFLICT", "PROVENANCE_MISS", "DUPLICATE_EVENT",
        "SAFE_ABSTENTION",
    }
    assert required <= set(CROSS_SOURCE_FAILURES)


def test_classify_gmail_live_error_uses_code():
    assert classify_gmail_error(GmailLiveError("x", code="GMAIL_AUTH_FAILURE")) == "GMAIL_AUTH_FAILURE"
    assert classify_gmail_error(GmailLiveError("x", code="GMAIL_PARSE_FAILURE")) == "GMAIL_PARSE_FAILURE"
    assert classify_gmail_error(GmailLiveError("x", code="GMAIL_INGESTION_FAILURE")) == "GMAIL_INGESTION_FAILURE"


def test_classify_auth_error_and_missing_file():
    assert classify_gmail_error(GmailAuthError("no token")) == "GMAIL_AUTH_FAILURE"
    assert classify_gmail_error(FileNotFoundError("creds")) == "GMAIL_AUTH_FAILURE"


def test_classify_state_status():
    assert classify_state_status("conflict") == "CROSS_SOURCE_CONFLICT"
    assert classify_state_status("review") == "CROSS_SOURCE_CONFLICT"
    assert classify_state_status("absent") == "SAFE_ABSTENTION"
    assert classify_state_status("definitive") is None


def test_safe_abstention_is_not_a_defect():
    assert is_defect("SAFE_ABSTENTION") is False
    assert is_defect("GMAIL_AUTH_FAILURE") is True


def test_empty_and_merge_taxonomy():
    tax = empty_taxonomy()
    assert set(tax) == set(CROSS_SOURCE_FAILURES)
    assert all(v == 0 for v in tax.values())
    merge_taxonomy(tax, "DUPLICATE_EVENT")
    merge_taxonomy(tax, "DUPLICATE_EVENT")
    assert tax["DUPLICATE_EVENT"] == 2
    with pytest.raises(ValueError):
        merge_taxonomy(tax, "NOPE")


def test_parse_failure_surfaced_by_adapter(monkeypatch: pytest.MonkeyPatch):
    import continuum.sources.gmail.adapter as adapter_mod
    from continuum.sources.gmail.adapter import GmailAdapter
    from continuum.sources.gmail.models import GmailMessage, GmailParticipant

    def boom(_msg):
        raise ValueError("corrupt payload")

    monkeypatch.setattr(adapter_mod, "normalize_gmail_message", boom)
    adapter = GmailAdapter()
    msg = GmailMessage(
        message_id="bad", thread_id="t", subject="s", body="body",
        from_participant=GmailParticipant(name="X", email="x@y.com"),
    )
    with pytest.raises(GmailLiveError) as exc:
        adapter.normalize(msg)
    assert exc.value.code == "GMAIL_PARSE_FAILURE"
