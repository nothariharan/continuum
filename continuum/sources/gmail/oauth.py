"""Gmail OAuth and credential helpers.

Google client libraries are optional (``pip install '.[google]'``) and imported
lazily so importing this module never requires them. The one-time consent flow
(:func:`run_oauth_flow`) is meant to be driven by a human via the
``scripts/gmail_authorize.py`` helper; :func:`load_gmail_service` is what the
live client calls on every sync to obtain an authorized API resource.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Read-only Gmail access is all Continuum needs to ingest.
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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

    @property
    def resolved_token_path(self) -> Path:
        if self.token_path is not None:
            return self.token_path
        return self.credentials_path.with_name("gmail_token.json")


class GmailAuthError(RuntimeError):
    """OAuth/credential failure (missing deps, bad token, expired consent)."""


def _require_google() -> tuple[Any, Any, Any]:
    """Lazily import google client libs, raising a clear message if absent."""
    try:
        from google.auth.transport.requests import Request  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise GmailAuthError(
            "Gmail live sync needs the 'google' extra: pip install '.[google]' "
            "(google-api-python-client, google-auth-oauthlib)"
        ) from exc
    return Credentials, Request, build


def load_credentials(creds: GmailCredentials) -> Any:
    """Load cached user credentials, refreshing the access token if needed.

    Requires that consent has already been granted once (a token file exists).
    Raises :class:`GmailAuthError` with actionable guidance otherwise.
    """
    Credentials, Request, _ = _require_google()
    token_path = creds.resolved_token_path
    if not token_path.exists():
        raise GmailAuthError(
            f"No Gmail token at {token_path}. Run the one-time consent flow first: "
            "python scripts/gmail_authorize.py"
        )
    credentials = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            token_path.write_text(credentials.to_json(), encoding="utf-8")
        else:
            raise GmailAuthError(
                f"Gmail token at {token_path} is invalid and cannot refresh; re-run consent."
            )
    return credentials


def load_gmail_service(creds: GmailCredentials) -> Any:
    """Return an authorized Gmail API resource (``service``)."""
    _, _, build = _require_google()
    credentials = load_credentials(creds)
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def run_oauth_flow(creds: GmailCredentials, *, port: int = 0) -> Path:
    """Run the one-time browser consent flow and persist the token.

    Human-driven: opens a local browser for Google consent, then writes the
    resulting token to ``creds.resolved_token_path``. Returns the token path.
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise GmailAuthError(
            "Consent flow needs the 'google' extra: pip install '.[google]'"
        ) from exc
    if not creds.credentials_path.exists():
        raise FileNotFoundError(f"OAuth client secret not found: {creds.credentials_path}")
    flow = InstalledAppFlow.from_client_secrets_file(str(creds.credentials_path), GMAIL_SCOPES)
    credentials = flow.run_local_server(port=port)
    token_path = creds.resolved_token_path
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return token_path
