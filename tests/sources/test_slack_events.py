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


def _event_body(secret: str, ts: str, event_id: str = "evt-1") -> tuple[bytes, dict[str, str]]:
    body = json.dumps(
        {"type": "event_callback", "event_id": event_id, "event": {"type": "message", "channel": "C1", "ts": "123.45"}}
    ).encode()
    return body, {"X-Slack-Request-Timestamp": ts, "X-Slack-Signature": _sign(secret, body, ts)}


def test_gateway_accepts_valid_event():
    secret = "test-secret"
    received: list[dict] = []
    gw = SlackEventsGateway(signing_secret=secret, handler=received.append)
    body, headers = _event_body(secret, str(int(time.time())))
    code, resp = gw.handle_http(body, headers)
    assert code == 200
    assert len(received) == 1


def test_gateway_rejects_bad_signature():
    secret = "test-secret"
    received: list[dict] = []
    gw = SlackEventsGateway(signing_secret=secret, handler=received.append)
    body, headers = _event_body(secret, str(int(time.time())))
    headers["X-Slack-Signature"] = "v0=deadbeef"
    code, resp = gw.handle_http(body, headers)
    assert code == 401
    assert len(received) == 0


def test_gateway_rejects_stale_timestamp():
    secret = "test-secret"
    received: list[dict] = []
    gw = SlackEventsGateway(signing_secret=secret, handler=received.append)
    stale = str(int(time.time()) - 600)
    body, headers = _event_body(secret, stale)
    code, resp = gw.handle_http(body, headers)
    assert code == 401
    assert len(received) == 0


def test_gateway_rejects_missing_timestamp_header():
    secret = "test-secret"
    received: list[dict] = []
    gw = SlackEventsGateway(signing_secret=secret, handler=received.append)
    body, headers = _event_body(secret, str(int(time.time())))
    headers.pop("X-Slack-Request-Timestamp")
    code, resp = gw.handle_http(body, headers)
    assert code == 401
    assert len(received) == 0


def test_gateway_rejects_malformed_payload():
    secret = "test-secret"
    received: list[dict] = []
    gw = SlackEventsGateway(signing_secret=secret, handler=received.append)
    ts = str(int(time.time()))
    body = b"{not-json"
    headers = {"X-Slack-Request-Timestamp": ts, "X-Slack-Signature": _sign(secret, body, ts)}
    code, resp = gw.handle_http(body, headers)
    assert code == 400
    assert len(received) == 0


def test_gateway_deduplicates_replayed_event():
    secret = "test-secret"
    received: list[dict] = []
    gw = SlackEventsGateway(signing_secret=secret, handler=received.append)
    body, headers = _event_body(secret, str(int(time.time())), event_id="evt-dup")
    assert gw.handle_http(body, headers)[0] == 200
    code, resp = gw.handle_http(body, headers)
    assert code == 200
    assert resp.get("deduped") is True
    assert len(received) == 1
