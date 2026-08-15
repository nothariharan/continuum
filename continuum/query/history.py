"""Phase 1 entry point — thin wrapper over the generalized historical resolver."""

from __future__ import annotations

from continuum.hydradb import HydraDBClient
from .state import resolve_state_on


def owner_on(client: HydraDBClient, account_id: str, date: str) -> dict:
    return resolve_state_on(client, account_id, date, "OWNS")
