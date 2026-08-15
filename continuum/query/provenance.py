"""Phase 1 entry point — thin wrapper over the generalized provenance resolver."""

from __future__ import annotations

from continuum.hydradb import HydraDBClient
from .state import resolve_provenance


def ownership_provenance(client: HydraDBClient, account_id: str) -> dict:
    return resolve_provenance(client, account_id, "OWNS")
