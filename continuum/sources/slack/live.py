"""Slack Web API client for live ingestion."""

from __future__ import annotations

import json
import random
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime
from typing import Any

from .models import SlackMessage, SlackThreadFixture

_RETRYABLE_SLACK_ERRORS = {"ratelimited", "internal_error", "timeout", "fatal_error"}


class SlackAPIError(RuntimeError):
    """Typed Slack API failure, surfaced only after retries are exhausted."""

    def __init__(self, message: str, *, code: str | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class SlackWebClient:
    """Minimal Slack Web API client (no slack_sdk required for ingestion)."""

    BASE = "https://slack.com/api"

    def __init__(
        self,
        token: str,
        *,
        max_retries: int = 3,
        base_backoff: float = 0.2,
        max_backoff: float = 5.0,
        timeout: float = 30.0,
    ) -> None:
        self._token = token
        self._max_retries = max_retries
        self._base_backoff = base_backoff
        self._max_backoff = max_backoff
        self._timeout = timeout

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        """Retry-After seconds or HTTP-date -> seconds; None when absent."""
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            pass
        try:
            when = parsedate_to_datetime(value)
            return max(0.0, (when.timestamp() - time.time()))
        except (TypeError, ValueError, OverflowError):
            return None

    def _backoff(self, attempt: int, retry_after: float | None = None) -> float:
        if retry_after is not None:
            return min(retry_after, self._max_backoff)
        base = min(self._max_backoff, self._base_backoff * (2**attempt))
        return base * (0.5 + random.random())  # full-ish jitter

    def _call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = dict(params or {})
        data = urllib.parse.urlencode(params).encode("utf-8")
        last_error: str = ""
        for attempt in range(self._max_retries + 1):
            req = urllib.request.Request(
                f"{self.BASE}/{method}",
                data=data,
                headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600 or exc.code == 408
                if attempt < self._max_retries and retryable:
                    headers = getattr(exc, "headers", None) or getattr(exc, "hdrs", None) or {}
                    time.sleep(self._backoff(attempt, self._parse_retry_after(headers.get("Retry-After"))))
                    last_error = f"HTTP {exc.code}"
                    continue
                raise SlackAPIError(
                    f"Slack API {method} HTTP {exc.code}", code=str(exc.code), retryable=retryable
                ) from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as exc:
                if attempt < self._max_retries:
                    time.sleep(self._backoff(attempt))
                    last_error = str(exc)
                    continue
                raise SlackAPIError(f"Slack API {method} network error: {exc}", retryable=True) from exc

            if not payload.get("ok"):
                error = payload.get("error")
                retryable = error in _RETRYABLE_SLACK_ERRORS
                if attempt < self._max_retries and retryable:
                    time.sleep(self._backoff(attempt))
                    last_error = str(error)
                    continue
                raise SlackAPIError(f"Slack API {method} failed: {error}", code=error, retryable=retryable)
            return payload
        raise SlackAPIError(f"Slack API {method} exhausted retries: {last_error}", retryable=True)

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
