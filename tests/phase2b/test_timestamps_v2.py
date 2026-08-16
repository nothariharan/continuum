"""Timestamp resolver tests — deterministic time signals, no invented dates."""

from __future__ import annotations

from continuum.dataset.artifact import Artifact
from continuum.extract.v2.envelope import build_envelope
from continuum.extract.v2.timestamps import resolve_timestamps


def _envelope(content: str, timestamp: str | None = None, source: str = "fireflies"):
    artifact = Artifact(
        id="dsid_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        source=source,
        source_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        type="fireflies",
        author=None,
        timestamp=timestamp,
        title="LucentGrid POC",
        content=content,
        metadata={},
    )
    return build_envelope(artifact)


def test_artifact_timestamp_wins():
    observed, valid_from, valid_to, source = resolve_timestamps(
        _envelope("Owner: Sarah Chen - Send summary", timestamp="2026-07-29T00:00:00")
    )
    assert observed == "2026-07-29T00:00:00"
    assert source == "artifact"
    assert valid_from is None
    assert valid_to is None


def test_meeting_date_fallback():
    observed, _, _, source = resolve_timestamps(
        _envelope("Header:\n- Date: 2026-09-09\n- Start: 15:00 PDT")
    )
    assert observed == "2026-09-09"
    assert source == "meeting-date"


def test_revision_history_last_date():
    observed, _, _, source = resolve_timestamps(
        _envelope("Revision history\n- 2025-03-12: initial draft\n- 2026-11-02: tuned alpha")
    )
    assert observed == "2026-11-02"
    assert source == "revision-history"


def test_text_timeline_last_date():
    observed, _, _, source = resolve_timestamps(
        _envelope("2025-11-12 - inbound form\n2026-01-14 - pricing conversation")
    )
    assert observed == "2026-01-14"
    assert source == "text-timeline"


def test_no_timestamp_no_signal():
    observed, _, _, source = resolve_timestamps(_envelope("Owner: Sarah Chen - Send summary"))
    assert observed is None
    assert source is None


def test_no_invented_validity():
    observed, valid_from, valid_to, _ = resolve_timestamps(
        _envelope("Sarah Chen owns Acme Health.", timestamp="2026-07-29T00:00:00")
    )
    assert observed == "2026-07-29T00:00:00"
    assert valid_from is None
    assert valid_to is None


def test_explicit_valid_from():
    observed, valid_from, valid_to, _ = resolve_timestamps(
        _envelope("Sarah takes over Acme Health starting 2026-08-20.", timestamp="2026-07-29T00:00:00")
    )
    assert valid_from == "2026-08-20"
    assert valid_to is None


def test_explicit_valid_to():
    observed, valid_from, valid_to, _ = resolve_timestamps(
        _envelope("Sarah leads the account until 2027-01-15.", timestamp="2026-07-29T00:00:00")
    )
    assert valid_to == "2027-01-15"
    assert valid_from is None


def test_relative_date_not_converted():
    observed, valid_from, valid_to, _ = resolve_timestamps(
        _envelope("Sarah owns Acme. Handoff next Monday.", timestamp="2026-07-29T00:00:00")
    )
    assert observed == "2026-07-29T00:00:00"
    assert valid_from is None


def test_valid_to_not_before_valid_from():
    observed, valid_from, valid_to, _ = resolve_timestamps(
        _envelope("Sarah owns Acme starting 2026-08-20 until 2026-07-01.", timestamp="2026-07-29T00:00:00")
    )
    assert valid_from == "2026-08-20"
    assert valid_to is None
