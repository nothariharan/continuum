"""Slack Events API gateway — validate, ACK fast, enqueue."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

EventHandler = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class SlackEventEnvelope:
    event_id: str
    event_type: str
    payload: dict[str, Any]
    received_at: float


def verify_slack_signature(
    signing_secret: str,
    body: bytes,
    timestamp: str,
    signature: str,
    *,
    max_age_seconds: int = 300,
) -> bool:
    if abs(time.time() - int(timestamp)) > max_age_seconds:
        return False
    base = f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8")
    digest = hmac.new(signing_secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature)


class SlackEventsGateway:
    """ACK immediately; process events via handler (never block on pipeline)."""

    def __init__(self, *, signing_secret: str, handler: EventHandler) -> None:
        self._signing_secret = signing_secret
        self._handler = handler
        self._seen: set[str] = set()

    def handle_http(
        self,
        body: bytes,
        headers: dict[str, str],
    ) -> tuple[int, dict[str, Any]]:
        timestamp = headers.get("X-Slack-Request-Timestamp", headers.get("x-slack-request-timestamp", ""))
        signature = headers.get("X-Slack-Signature", headers.get("x-slack-signature", ""))
        if not verify_slack_signature(self._signing_secret, body, timestamp, signature):
            return 401, {"error": "invalid signature"}

        payload = json.loads(body.decode("utf-8"))
        if payload.get("type") == "url_verification":
            return 200, {"challenge": payload.get("challenge")}

        event = payload.get("event") or {}
        event_id = payload.get("event_id") or event.get("client_msg_id") or event.get("ts", "")
        if event_id and event_id in self._seen:
            return 200, {"ok": True, "deduped": True}
        if event_id:
            self._seen.add(event_id)

        envelope = SlackEventEnvelope(
            event_id=str(event_id),
            event_type=str(event.get("type") or payload.get("type") or "unknown"),
            payload=payload,
            received_at=time.time(),
        )
        self._handler(envelope.payload)
        return 200, {"ok": True}
