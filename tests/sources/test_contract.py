"""Tests for source ingestion contract and Artifact.from_source_record."""

from __future__ import annotations

import json

import pytest

from continuum.dataset.artifact import (
    ARTIFACT_ID_RE,
    Artifact,
    artifact_from_dict,
    artifact_id_from_native,
    artifact_to_dict,
)
from continuum.sources.validate import validate_artifact_boundary


def test_from_source_record_produces_valid_dsid_id():
    artifact = Artifact.from_source_record(
        source="slack",
        native_source_id="C07ABC:1728291000.123456",
        type="slack_message",
        content="Sarah Chen: Taking over Acme account.",
        author="Sarah Chen",
        timestamp="2026-07-28T14:30:00+00:00",
        title="#handoffs",
        metadata={"message_id": "1728291000.123456", "channel_id": "C07ABC"},
    )
    assert ARTIFACT_ID_RE.match(artifact.id)
    assert artifact.source_id == "C07ABC:1728291000.123456"
    assert artifact.metadata["native_source_id"] == "C07ABC:1728291000.123456"


def test_from_source_record_idempotent():
    kwargs = dict(
        source="slack",
        native_source_id="C07ABC:1728291000.123456",
        type="slack_message",
        content="Hello",
    )
    a1 = Artifact.from_source_record(**kwargs)
    a2 = Artifact.from_source_record(**kwargs)
    assert a1.id == a2.id
    assert artifact_id_from_native("slack", "C07ABC:1728291000.123456") == a1.id


def test_different_sources_same_native_id_different_artifact_ids():
    native = "MSG-001"
    slack_id = artifact_id_from_native("slack", native)
    gmail_id = artifact_id_from_native("gmail", native)
    assert slack_id != gmail_id


def test_artifact_dict_round_trip():
    original = Artifact.from_source_record(
        source="gmail",
        native_source_id="msg-abc123",
        type="gmail_message",
        content="From: soham@company.com\nSubject: Handoff\n\nBody.",
        author="soham@company.com",
        metadata={"message_id": "msg-abc123", "thread_id": "thread-xyz"},
    )
    payload = artifact_to_dict(original)
    line = json.dumps(payload)
    restored = artifact_from_dict(json.loads(line))
    assert restored == original


def test_validate_artifact_boundary_requires_metadata_when_flagged():
    artifact = Artifact.from_source_record(
        source="slack",
        native_source_id="C07:1.2",
        type="slack_message",
        content="text",
    )
    validate_artifact_boundary(artifact)
    with pytest.raises(ValueError, match="missing metadata"):
        validate_artifact_boundary(artifact, require_metadata=True)


def test_from_source_record_rejects_empty_native_id():
    with pytest.raises(ValueError, match="native_source_id"):
        Artifact.from_source_record(
            source="slack",
            native_source_id="  ",
            type="slack_message",
            content="x",
        )


def test_from_source_record_rejects_unsupported_source():
    with pytest.raises(ValueError, match="unsupported source"):
        Artifact.from_source_record(
            source="twitter",
            native_source_id="1",
            type="tweet",
            content="x",
        )
