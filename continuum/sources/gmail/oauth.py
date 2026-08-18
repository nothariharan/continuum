"""Gmail OAuth and credential helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GmailCredentials:
    credentials_path: Path
    token_path: Path | None = None

    @classmethod
    def from_env(cls) -> GmailCredentials:
        path = os.environ.get("GMAIL_CREDENTIALS_PATH", "").strip()
        if not path:
            raise ValueError("GMAIL_CREDENTIALS_PATH is required for live Gmail")
        token = os.environ.get("GMAIL_TOKEN_PATH")
        return cls(credentials_path=Path(path), token_path=Path(token) if token else None)
