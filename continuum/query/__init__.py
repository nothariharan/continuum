"""Fixed, machine-readable Phase 1 graph queries."""

from .conflicts import find_conflicts
from .current_state import current_owner
from .history import owner_on
from .provenance import ownership_provenance

__all__ = ["current_owner", "find_conflicts", "owner_on", "ownership_provenance"]

