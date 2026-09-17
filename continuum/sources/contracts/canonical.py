"""CanonicalDocument — tenant-scoped normalized unit for workers and graph handoff."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from continuum.dataset.artifact import Artifact


@dataclass(frozen=True)
class CanonicalDocument:
    document_id: str
    tenant_id: str
    source_type: str
    native_id: str
    author_id: str
    author_display: str
    channel_or_container: str
    title: str | None
    content: str
    timestamp: datetime
    raw_metadata: dict[str, Any] = field(default_factory=dict)


def _parse_artifact_timestamp(value: str | None) -> datetime:
    if not value or not value.strip():
        raise ValueError("artifact timestamp is required for CanonicalDocument")
    normalized = value.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _author_id_from_artifact(artifact: Artifact) -> str:
    meta = artifact.metadata
    for key in ("user_id", "author_id", "from_email", "sender_id"):
        raw = meta.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    if artifact.author and artifact.author.strip():
        return artifact.author.strip()
    return "unknown"


def _channel_or_container_from_artifact(artifact: Artifact) -> str:
    meta = artifact.metadata
    for key in ("channel_id", "channel_name", "thread_id", "mailbox"):
        raw = meta.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    if artifact.title and artifact.title.strip():
        return artifact.title.strip()
    return artifact.source


def artifact_to_canonical_document(
    artifact: Artifact,
    *,
    tenant_id: str,
) -> CanonicalDocument:
    """Map boundary Artifact to production CanonicalDocument."""
    if not tenant_id.strip():
        raise ValueError("tenant_id is required")

    native_id = artifact.source_id.strip() or str(
        artifact.metadata.get("native_source_id") or ""
    ).strip()
    if not native_id:
        raise ValueError("artifact must have source_id or metadata.native_source_id")

    author_display = (artifact.author or "unknown").strip() or "unknown"

    return CanonicalDocument(
        document_id=artifact.id,
        tenant_id=tenant_id.strip(),
        source_type=artifact.source,
        native_id=native_id,
        author_id=_author_id_from_artifact(artifact),
        author_display=author_display,
        channel_or_container=_channel_or_container_from_artifact(artifact),
        title=artifact.title,
        content=artifact.content,
        timestamp=_parse_artifact_timestamp(artifact.timestamp),
        raw_metadata=dict(artifact.metadata),
    )
