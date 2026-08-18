"""Tests for Gmail live scaffold — explicit failure states, no fake success."""

from __future__ import annotations

from pathlib import Path

import pytest

from continuum.sources.gmail.live import GmailLiveClient
from continuum.sources.gmail.oauth import GmailCredentials


def test_live_client_requires_credentials_file(tmp_path: Path):
    client = GmailLiveClient(credentials_path=tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError, match="credentials not found"):
        client.authenticate()


def test_live_client_list_messages_not_wired(tmp_path: Path):
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    client = GmailLiveClient(credentials_path=creds)
    with pytest.raises(NotImplementedError, match="list_messages"):
        client.list_messages()


def test_live_client_get_message_not_wired(tmp_path: Path):
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    client = GmailLiveClient(credentials_path=creds)
    with pytest.raises(NotImplementedError, match="not wired"):
        client.get_message("msg-1")


def test_credentials_from_env_requires_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GMAIL_CREDENTIALS_PATH", raising=False)
    with pytest.raises(ValueError, match="GMAIL_CREDENTIALS_PATH is required"):
        GmailCredentials.from_env()
