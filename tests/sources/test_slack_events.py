"""Tests for Slack events gateway."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

from continuum.sources.slack.events import SlackEventsGateway, verify_slack_signature


def _sign(secret: str, body: bytes, ts: str) -> str:
    base = f"v0:{ts}:{body.decode()}".encode()
    digest = hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return f"v0={digest}"


def test_verify_signature():
    secret = "test-secret"
    body = b'{"type":"event_callback"}'
    ts = str(int(time.time()))
    sig = _sign(secret, body, ts)
    assert verify_slack_signature(secret, body, ts, sig)


def test_gateway_url_verification():
    secret = "test-secret"
    received: list[dict] = []
    gw = SlackEventsGateway(signing_secret=secret, handler=received.append)
    body = json.dumps({"type": "url_verification", "challenge": "abc"}).encode()
    ts = str(int(time.time()))
    code, resp = gw.handle_http(body, {"X-Slack-Request-Timestamp": ts, "X-Slack-Signature": _sign(secret, body, ts)})
    assert code == 200
    assert resp["challenge"] == "abc"
