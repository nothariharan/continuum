"""Boundary validation for ingested Artifacts."""

from __future__ import annotations

from continuum.dataset.artifact import ARTIFACT_ID_RE, Artifact
from continuum.dataset.manifest import SOURCE_ALIASES

REQUIRED_METADATA_BY_SOURCE: dict[str, frozenset[str]] = {
    "slack": frozenset({"message_id", "channel_id"}),
    "gmail": frozenset({"message_id", "thread_id"}),
    "github": frozenset({"message_id"}),
    "jira": frozenset({"message_id"}),
}


def validate_artifact_boundary(artifact: Artifact, *, require_metadata: bool = False) -> None:
    """Raise ValueError if artifact violates the ingestion boundary."""
    if artifact.source not in SOURCE_ALIASES:
        raise ValueError(f"unsupported source: {artifact.source}")
    if not ARTIFACT_ID_RE.match(artifact.id):
        raise ValueError(f"invalid artifact id: {artifact.id}")
    if not artifact.source_id.strip():
        raise ValueError("source_id must be non-empty")
    if not artifact.content.strip():
        raise ValueError("content must be non-empty")
    if not artifact.type.strip():
        raise ValueError("type must be non-empty")

    if require_metadata:
        required = REQUIRED_METADATA_BY_SOURCE.get(artifact.source, frozenset())
        missing = required - set(artifact.metadata)
        if missing:
            raise ValueError(f"missing metadata keys for {artifact.source}: {sorted(missing)}")
