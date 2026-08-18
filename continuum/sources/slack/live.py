"""Slack Web API client for live ingestion."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .models import SlackMessage, SlackThreadFixture


class SlackWebClient:
    """Minimal Slack Web API client (no slack_sdk required for ingestion)."""

    BASE = "https://slack.com/api"

    def __init__(self, token: str) -> None:
        self._token = token

    def _call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = dict(params or {})
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(
            f"{self.BASE}/{method}",
            data=data,
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(f"Slack API {method} failed: {payload.get('error')}")
        return payload

    def auth_test(self) -> dict[str, Any]:
        return self._call("auth.test")

    def conversations_history(
        self,
        channel_id: str,
        *,
        cursor: str | None = None,
        limit: int = 100,
        oldest: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"channel": channel_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        if oldest:
            params["oldest"] = oldest
        return self._call("conversations.history", params)

    def conversations_replies(self, channel_id: str, ts: str, *, limit: int = 100) -> dict[str, Any]:
        return self._call("conversations.replies", {"channel": channel_id, "ts": ts, "limit": limit})

    def users_info(self, user_id: str) -> dict[str, Any]:
        return self._call("users.info", {"user": user_id})

    def message_from_api(
        self,
        message: dict[str, Any],
        *,
        channel_id: str,
        channel_name: str,
        workspace_id: str,
        workspace_subdomain: str,
        users: dict[str, dict[str, Any]],
    ) -> SlackMessage:
        fixture = SlackThreadFixture(
            channel_id=channel_id,
            channel_name=channel_name,
            workspace_id=workspace_id,
            workspace_subdomain=workspace_subdomain,
            messages=[message],
            replies={},
            users=users,
        )
        return fixture.to_messages()[0]
