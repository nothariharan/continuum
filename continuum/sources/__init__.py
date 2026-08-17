"""Source ingestion layer — adapters terminate at the canonical Artifact boundary."""

from continuum.sources.connector import FetchResult, SourceConnector
from continuum.sources.cursor import SyncCursor

__all__ = ["FetchResult", "SourceConnector", "SyncCursor"]
