"""Tests for M0 production ingestion contracts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from continuum.dataset.artifact import Artifact
from continuum.sources.contracts import (
    ChannelSelection,
    IngestionHandoff,
    IngestionJobProgress,
    IngestionJobStatus,
    SlackInstallState,
    TenantContext,
    artifact_to_canonical_document,
)


def test_artifact_to_canonical_document_slack():
    artifact = Artifact.from_source_record(
        source="slack",
        native_source_id="C07ABC:1728291000.123456",
        type="slack_message",
        content="Sarah Chen: Taking over Acme account.",
        author="Sarah Chen",
        timestamp="2026-07-28T14:30:00+00:00",
        title="#handoffs",
        metadata={
            "message_id": "1728291000.123456",
            "channel_id": "C07ABC",
            "user_id": "U123",
        },
    )
    doc = artifact_to_canonical_document(artifact, tenant_id="org_acme")
    assert doc.document_id == artifact.id
    assert doc.tenant_id == "org_acme"
    assert doc.source_type == "slack"
    assert doc.native_id == "C07ABC:1728291000.123456"
    assert doc.author_id == "U123"
    assert doc.channel_or_container == "C07ABC"
    assert doc.timestamp == datetime(2026, 7, 28, 14, 30, tzinfo=timezone.utc)


def test_artifact_to_canonical_document_requires_tenant_id():
    artifact = Artifact.from_source_record(
        source="slack",
        native_source_id="C07ABC:1.0",
        type="slack_message",
        content="hello",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises(ValueError, match="tenant_id"):
        artifact_to_canonical_document(artifact, tenant_id="  ")


def test_ingestion_handoff_carries_context_and_document():
    artifact = Artifact.from_source_record(
        source="slack",
        native_source_id="C07ABC:1.0",
        type="slack_message",
        content="hello",
        timestamp="2026-01-01T00:00:00+00:00",
        metadata={"channel_id": "C07ABC"},
    )
    ctx = TenantContext(tenant_id="org_acme", workspace_id="ws_main")
    doc = artifact_to_canonical_document(artifact, tenant_id=ctx.tenant_id)
    handoff = IngestionHandoff(context=ctx, document=doc)
    assert handoff.context.workspace_id == "ws_main"
    assert handoff.document.tenant_id == ctx.tenant_id


def test_ingestion_job_progress_fraction():
    progress = IngestionJobProgress(
        job_id="job_1",
        tenant_id="org_acme",
        workspace_id="ws_main",
        source="slack",
        status=IngestionJobStatus.BACKFILLING_MESSAGES,
        messages_processed=14200,
        messages_total=50000,
    )
    assert progress.fraction_complete == pytest.approx(0.284)
    assert progress.status == IngestionJobStatus.BACKFILLING_MESSAGES


def test_slack_install_and_channel_selection_frozen():
    install = SlackInstallState(
        state="nonce-abc",
        tenant_id="org_acme",
        workspace_id="ws_main",
        redirect_uri="https://app.continuum.example/oauth/slack/callback",
    )
    channels = (
        ChannelSelection(channel_id="C1", included=True, channel_name="general"),
        ChannelSelection(channel_id="C2", included=False, is_private=True),
    )
    assert install.state == "nonce-abc"
    assert channels[0].included is True
    assert channels[1].is_private is True
