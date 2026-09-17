"""Production ingestion interfaces (M0 contract-first).

Teammate-owned DTOs and protocols for OAuth, workers, and founder handoff.
Implementation of auth storage and graph load lives outside this package.
"""

from .canonical import CanonicalDocument, artifact_to_canonical_document
from .context import TenantContext
from .credentials import ConnectorCredentialsStore
from .handoff import IngestionHandoff
from .ingestion import IngestionJobProgress, IngestionJobStatus
from .slack_install import ChannelSelection, SlackInstallState

__all__ = [
    "CanonicalDocument",
    "ChannelSelection",
    "ConnectorCredentialsStore",
    "IngestionHandoff",
    "IngestionJobProgress",
    "IngestionJobStatus",
    "SlackInstallState",
    "TenantContext",
    "artifact_to_canonical_document",
]
