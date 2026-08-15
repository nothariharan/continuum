"""Phase 1 entry points — thin wrappers over the generalized state resolvers.

Kept for backward compatibility; behavior and output shape are identical to
`resolve_state` (same canonical envelope)."""

from __future__ import annotations

from continuum.hydradb import HydraDBClient
from .state import resolve_state


def current_owner(client: HydraDBClient, account_id: str) -> dict:
    return resolve_state(client, account_id, "OWNS")
