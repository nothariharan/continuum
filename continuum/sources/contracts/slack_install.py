"""Slack OAuth install and channel selection DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlackInstallState:
    """OAuth CSRF state bound to a Continuum tenant before redirect."""

    state: str
    tenant_id: str
    workspace_id: str
    redirect_uri: str


@dataclass(frozen=True)
class ChannelSelection:
    channel_id: str
    included: bool
    channel_name: str | None = None
    is_private: bool = False
