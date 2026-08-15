"""Phase 1 entry point — thin wrapper over the generalized conflict resolver."""

from __future__ import annotations

from continuum.hydradb import HydraDBClient
from .state import resolve_conflicts


def find_conflicts(client: HydraDBClient, account_id: str) -> dict:
    return resolve_conflicts(client, account_id, "OWNS")
