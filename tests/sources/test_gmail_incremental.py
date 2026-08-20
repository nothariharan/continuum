"""Gmail incremental sync lifecycle (Sections 13, 21).

Exercises the connector-agnostic ConnectorSyncLifecycle over the live Gmail
adapter with an injected fake service: initial sync watermarks the historyId,
incremental sync only pulls changes since the cursor, a worker restart resumes
from the persisted cursor (no in-memory state), and a replay with nothing new
does not reprocess the mailbox.
"""

from __future__ import annotations

from pathlib import Path

from continuum.sources.cursor import SyncCursor
from continuum.sources.gmail.adapter import GmailAdapter
from continuum.sources.gmail.live import GmailLiveClient
from continuum.sources.lifecycle import ConnectorSyncLifecycle
from continuum.sources.sync import load_cursor

from .test_gmail_live import FakeGmailService, _full_message


def _svc() -> FakeGmailService:
    svc = FakeGmailService()
    svc.add(_full_message("m1", "t1", "Acme", "Morgan owns Acme.", "Morgan <morgan@company.com>", "1690000000000"))
    svc.add(_full_message("m2", "t1", "Acme", "Priya will help.", "Priya <priya@company.com>", "1690100000000"))
    return svc


def _life(svc: FakeGmailService, cursor_path: Path) -> ConnectorSyncLifecycle:
    # A fresh lifecycle each call models a worker restart: no in-memory _seen,
    # state resumes only from the persisted cursor on disk.
    adapter = GmailAdapter(live_client=GmailLiveClient(service=svc))
    return ConnectorSyncLifecycle(adapter, cursor_path=cursor_path)


def test_initial_sync_watermarks_history_id(tmp_path: Path):
    svc = _svc()
    cursor_path = tmp_path / "gmail.cursor.json"
    result = _life(svc, cursor_path).initial_sync(limit=10)
    assert {a.source_id for a in result.artifacts} == {"m1", "m2"}
    assert cursor_path.exists()
    assert load_cursor(cursor_path).value == "1000"  # historyId watermark


def test_incremental_after_restart_pulls_only_new(tmp_path: Path):
    svc = _svc()
    cursor_path = tmp_path / "gmail.cursor.json"
    _life(svc, cursor_path).initial_sync(limit=10)

    # A new message arrives; Gmail advances the mailbox historyId.
    svc.add(_full_message("m3", "t1", "Acme", "Effective Aug 1, ownership of Acme transfers from Morgan to Priya.", "Morgan <morgan@company.com>", "1690200000000"))
    svc.history_added = ["m3"]
    svc.current_history_id = "1100"

    # Worker restart: brand-new lifecycle, resumes from the persisted cursor.
    inc = _life(svc, cursor_path).incremental_sync(limit=10)
    assert [a.source_id for a in inc.artifacts] == ["m3"]
    assert load_cursor(cursor_path).value == "1100"


def test_replay_with_nothing_new_does_not_reprocess(tmp_path: Path):
    svc = _svc()
    cursor_path = tmp_path / "gmail.cursor.json"
    _life(svc, cursor_path).initial_sync(limit=10)

    # Nothing changed since the cursor -> incremental returns nothing, and the
    # whole mailbox is NOT reprocessed.
    svc.history_added = []
    inc = _life(svc, cursor_path).incremental_sync(limit=10)
    assert inc.artifacts == []


def test_reingesting_same_message_is_idempotent(tmp_path: Path):
    # Re-delivery of the same native message yields the SAME artifact id, so a
    # downstream idempotent load never double-counts a replayed event.
    svc = _svc()
    adapter = GmailAdapter(live_client=GmailLiveClient(service=svc))
    a1 = adapter.normalize(adapter._client().get_message("m1"))
    a2 = adapter.normalize(adapter._client().get_message("m1"))
    assert a1.id == a2.id


def test_expired_history_id_triggers_bounded_resync(tmp_path: Path):
    from tests.sources.test_gmail_live import _HttpError

    svc = _svc()
    svc.history_error = _HttpError(404)
    adapter = GmailAdapter(live_client=GmailLiveClient(service=svc))
    # Too-old cursor: History API 404s -> bounded resync, not a silent stall.
    result = adapter.fetch(cursor=SyncCursor(source="gmail", value="1"), limit=10)
    assert {a.source_id for a in [adapter.normalize(r) for r in result.records]} == {"m1", "m2"}
