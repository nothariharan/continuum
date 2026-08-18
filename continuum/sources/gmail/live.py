"""Gmail live API stub — OAuth path for incremental sync."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import GmailMessage


class GmailLiveClient:
    """Placeholder for Gmail API integration.

    Live sync requires Google OAuth credentials on disk. This client validates
    credential presence and raises clear errors until credentials are configured.
    """

    def __init__(self, credentials_path: Path, token_path: Path | None = None) -> None:
        self._credentials_path = credentials_path
        self._token_path = token_path

    def authenticate(self) -> None:
        if not self._credentials_path.exists():
            raise FileNotFoundError(f"Gmail credentials not found: {self._credentials_path}")

    def list_messages(self, *, query: str = "", max_results: int = 100) -> list[dict[str, Any]]:
        self.authenticate()
        raise NotImplementedError(
            "Gmail live list_messages requires google-api-python-client; "
            "install optional delivery deps and configure OAuth token"
        )

    def get_message(self, message_id: str) -> GmailMessage:
        self.authenticate()
        raise NotImplementedError(f"Gmail live get_message({message_id}) not wired yet")
