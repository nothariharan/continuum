"""Tests for Gmail live client credential/auth guards (no network, no deps)."""

from __future__ import annotations

from pathlib import Path

import pytest

from continuum.sources.gmail.live import GmailLiveClient, GmailLiveError
from continuum.sources.gmail.oauth import GmailCredentials


def test_live_client_requires_credentials_file(tmp_path: Path):
    client = GmailLiveClient(credentials_path=tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError, match="credentials not found"):
        client.authenticate()


def test_live_client_requires_credentials_path_when_no_service():
    client = GmailLiveClient()
    with pytest.raises(GmailLiveError, match="credentials_path is required"):
        client.authenticate()


def test_injected_service_skips_credentials(tmp_path: Path):
    # A pre-built service bypasses all credential handling.
    client = GmailLiveClient(service=object())
    client.authenticate()  # no error


def test_credentials_from_env_requires_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GMAIL_CREDENTIALS_PATH", raising=False)
    with pytest.raises(ValueError, match="GMAIL_CREDENTIALS_PATH is required"):
        GmailCredentials.from_env()


def test_resolved_token_path_defaults_next_to_credentials(tmp_path: Path):
    creds = GmailCredentials(credentials_path=tmp_path / "credentials.json")
    assert creds.resolved_token_path == tmp_path / "gmail_token.json"
