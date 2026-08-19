"""Batch 2 — SlackWebClient._call bounded retry + typed error (unit, no network)."""

from __future__ import annotations

import io
import json
from unittest import mock

import urllib.error

from continuum.sources.slack.live import SlackAPIError, SlackWebClient


def _client(**kwargs) -> SlackWebClient:
    kwargs.setdefault("max_retries", 3)
    kwargs.setdefault("base_backoff", 0.0)
    kwargs.setdefault("max_backoff", 0.0)
    kwargs.setdefault("timeout", 1.0)
    return SlackWebClient("xoxb-test", **kwargs)


def _ok(**payload):
    payload.setdefault("ok", True)
    payload.setdefault("team_id", "T1")
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


def test_retries_on_429_then_succeeds():
    calls = {"n": 0}

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "ratelimited", {}, None)
        return _ok()

    with mock.patch("urllib.request.urlopen", new=fake_urlopen):
        payload = _client()._call("auth.test")
    assert payload["ok"] is True
    assert calls["n"] == 3


def test_exhausts_retries_then_raises_typed_error():
    def fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)

    with mock.patch("urllib.request.urlopen", new=fake_urlopen):
        try:
            _client()._call("conversations.history", {"channel": "C1"})
            raised = False
        except SlackAPIError as exc:
            raised = True
            assert exc.retryable is True
    assert raised


def test_no_retry_on_4xx():
    calls = {"n": 0}

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 403, "forbidden", {}, None)

    with mock.patch("urllib.request.urlopen", new=fake_urlopen):
        try:
            _client()._call("auth.test")
            raised = False
        except SlackAPIError as exc:
            raised = True
            assert exc.retryable is False
    assert raised
    assert calls["n"] == 1


def test_retries_on_network_error_then_succeeds():
    calls = {"n": 0}

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.URLError("connection reset")
        return _ok()

    with mock.patch("urllib.request.urlopen", new=fake_urlopen):
        assert _client()._call("auth.test")["ok"] is True
    assert calls["n"] == 2


def test_slack_ratelimited_flag_retries():
    calls = {"n": 0}

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        if calls["n"] < 2:
            return _ok(ok=False, error="ratelimited")
        return _ok()

    with mock.patch("urllib.request.urlopen", new=fake_urlopen):
        assert _client()._call("auth.test")["ok"] is True
    assert calls["n"] == 2


def test_non_retryable_slack_error_raises_immediately():
    calls = {"n": 0}

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        return _ok(ok=False, error="invalid_auth")

    with mock.patch("urllib.request.urlopen", new=fake_urlopen):
        try:
            _client()._call("auth.test")
            raised = False
        except SlackAPIError as exc:
            raised = True
            assert exc.code == "invalid_auth"
            assert exc.retryable is False
    assert raised
    assert calls["n"] == 1


def test_parse_retry_after_seconds_and_date():
    assert SlackWebClient._parse_retry_after("7") == 7.0
    assert SlackWebClient._parse_retry_after(None) is None
    assert SlackWebClient._parse_retry_after("") is None
    when = SlackWebClient._parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT")
    assert when is not None and when >= 0.0
