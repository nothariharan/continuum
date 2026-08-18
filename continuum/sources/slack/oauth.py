"""Slack OAuth and credential helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SlackCredentials:
    bot_token: str
    signing_secret: str | None = None
    app_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None

    @classmethod
    def from_env(cls) -> SlackCredentials:
        token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("SLACK_BOT_TOKEN is required for live Slack")
        return cls(
            bot_token=token,
            signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
            app_token=os.environ.get("SLACK_APP_TOKEN"),
            client_id=os.environ.get("SLACK_CLIENT_ID"),
            client_secret=os.environ.get("SLACK_CLIENT_SECRET"),
        )

    def health_detail(self) -> str:
        parts = ["bot_token=set"]
        if self.signing_secret:
            parts.append("signing_secret=set")
        if self.app_token:
            parts.append("app_token=set")
        return ", ".join(parts)
