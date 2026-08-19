"""Live Gmail client + adapter tests using an injected fake API service.

No google packages, no network, no credentials — the fake mirrors the
``googleapiclient`` resource chain (``svc.users().messages().get(...).execute()``)
so we exercise the real GmailLiveClient / GmailAdapter code paths deterministically.
"""

from __future__ import annotations

import base64

import pytest

from continuum.sources.gmail.adapter import GmailAdapter
from continuum.sources.gmail.live import GmailLiveClient, GmailLiveError


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _full_message(mid: str, thread: str, subject: str, body: str, sender: str, internal_ms: str) -> dict:
    return {
        "id": mid,
        "threadId": thread,
        "internalDate": internal_ms,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": sender},
                {"name": "To", "value": "team@company.com"},
                {"name": "Subject", "value": subject},
            ],
            "body": {"data": _b64url(body)},
        },
    }


class _Req:
    def __init__(self, value):
        self._value = value

    def execute(self):
        if isinstance(self._value, Exception):
            raise self._value
        return self._value


class _Messages:
    def __init__(self, svc):
        self._svc = svc

    def list(self, *, userId, q="", maxResults=100, pageToken=None):
        # Single page of ids honoring maxResults.
        ids = [{"id": mid} for mid in self._svc.message_order[:maxResults]]
        return _Req({"messages": ids})

    def get(self, *, userId, id, format="full"):
        if id not in self._svc.messages:
            return _Req(_HttpError(404))
        return _Req(self._svc.messages[id])


class _History:
    def __init__(self, svc):
        self._svc = svc

    def list(self, *, userId, startHistoryId, historyTypes=None, maxResults=100, pageToken=None):
        if self._svc.history_error is not None:
            return _Req(self._svc.history_error)
        added = [
            {"messagesAdded": [{"message": {"id": mid}}]}
            for mid in self._svc.history_added
        ]
        return _Req({"history": added, "historyId": self._svc.current_history_id})


class _Users:
    def __init__(self, svc):
        self._svc = svc

    def messages(self):
        return _Messages(self._svc)

    def history(self):
        return _History(self._svc)

    def getProfile(self, *, userId):
        return _Req({"historyId": self._svc.current_history_id})


class _HttpError(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")

        class _Resp:
            pass

        self.resp = _Resp()
        self.resp.status = status


class FakeGmailService:
    def __init__(self):
        self.messages: dict[str, dict] = {}
        self.message_order: list[str] = []
        self.history_added: list[str] = []
        self.history_error: Exception | None = None
        self.current_history_id = "1000"

    def add(self, message: dict) -> None:
        self.messages[message["id"]] = message
        self.message_order.insert(0, message["id"])  # newest first

    def users(self):
        return _Users(self)


@pytest.fixture
def service() -> FakeGmailService:
    svc = FakeGmailService()
    svc.add(_full_message("m1", "t1", "Acme ownership", "Morgan owns Acme.", "Morgan <morgan@company.com>", "1690000000000"))
    svc.add(_full_message("m2", "t1", "Re: Acme ownership", "Priya will take over Acme.", "Priya <priya@company.com>", "1690100000000"))
    return svc


def test_list_and_get_messages(service: FakeGmailService):
    client = GmailLiveClient(service=service)
    ids = client.list_message_ids(max_results=10)
    assert ids == ["m2", "m1"]
    msg = client.get_message("m1")
    assert msg.subject == "Acme ownership"
    assert "Morgan owns Acme" in msg.body
    assert msg.from_participant.email == "morgan@company.com"
    # internalDate parsed to ISO UTC
    assert msg.timestamp.startswith("2023-07-22")


def test_list_messages_respects_limit(service: FakeGmailService):
    client = GmailLiveClient(service=service)
    assert len(client.list_messages(max_results=1)) == 1


def test_get_profile_history_id(service: FakeGmailService):
    client = GmailLiveClient(service=service)
    assert client.get_profile_history_id() == "1000"


def test_list_history_returns_added_ids(service: FakeGmailService):
    service.history_added = ["m2"]
    service.current_history_id = "1050"
    client = GmailLiveClient(service=service)
    ids, latest = client.list_history("1000")
    assert ids == ["m2"]
    assert latest == "1050"


def test_get_message_404_wrapped(service: FakeGmailService):
    client = GmailLiveClient(service=service)
    with pytest.raises(GmailLiveError) as exc:
        client.get_message("missing")
    assert exc.value.code == "GMAIL_INGESTION_FAILURE"


def test_auth_error_401_wrapped(service: FakeGmailService):
    service.history_error = _HttpError(401)
    client = GmailLiveClient(service=service)
    with pytest.raises(GmailLiveError) as exc:
        client.list_history("1")
    assert exc.value.code == "GMAIL_AUTH_FAILURE"


def test_retryable_500_flagged(service: FakeGmailService):
    service.history_error = _HttpError(503)
    client = GmailLiveClient(service=service)
    with pytest.raises(GmailLiveError) as exc:
        client.list_history("1")
    assert exc.value.retryable is True


# -- adapter live path ------------------------------------------------------


def test_adapter_initial_sync_live(service: FakeGmailService):
    adapter = GmailAdapter(live_client=GmailLiveClient(service=service))
    result = adapter.fetch(cursor=None, limit=10)
    assert {m.message_id for m in result.records} == {"m1", "m2"}
    assert result.next_cursor is not None
    assert result.next_cursor.value == "1000"  # historyId watermark
    artifacts = [adapter.normalize(m) for m in result.records]
    assert all(a.source == "gmail" for a in artifacts)


def test_adapter_incremental_sync_live(service: FakeGmailService):
    service.history_added = ["m2"]
    service.current_history_id = "1200"
    adapter = GmailAdapter(live_client=GmailLiveClient(service=service))
    from continuum.sources.cursor import SyncCursor

    cursor = SyncCursor(source="gmail", value="1000")
    result = adapter.fetch(cursor=cursor, limit=10)
    assert [m.message_id for m in result.records] == ["m2"]
    assert result.next_cursor.value == "1200"


def test_adapter_incremental_expired_history_falls_back(service: FakeGmailService):
    service.history_error = _HttpError(404)
    adapter = GmailAdapter(live_client=GmailLiveClient(service=service))
    from continuum.sources.cursor import SyncCursor

    cursor = SyncCursor(source="gmail", value="1")  # too old
    result = adapter.fetch(cursor=cursor, limit=10)
    # Falls back to bounded resync (all messages), not a silent stall.
    assert {m.message_id for m in result.records} == {"m1", "m2"}
