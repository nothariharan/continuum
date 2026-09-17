"""Payload crossing the ingestion → graph-load boundary."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical import CanonicalDocument
from .context import TenantContext


@dataclass(frozen=True)
class IngestionHandoff:
    """Emitted by workers; consumed by founder-owned graph/index loaders."""

    context: TenantContext
    document: CanonicalDocument
