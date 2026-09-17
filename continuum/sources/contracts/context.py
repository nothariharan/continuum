"""Tenant context injected into ingestion tasks and handoff payloads."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    workspace_id: str
    user_id: str | None = None
    role: str = "member"
