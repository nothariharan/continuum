"""Gmail live API client — OAuth-backed fetch for initial + incremental sync.

The Google client libraries (``google-api-python-client`` / ``google-auth``) are
optional dependencies (``pip install '.[google]'``). They are imported lazily so
the rest of Continuum runs without them. For tests, inject a fake ``service``
object that mimics the ``googleapiclient`` resource surface — no network, no
credentials, no google packages required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import GmailMessage
from .oauth import GmailCredentials, load_gmail_service


class GmailLiveError(RuntimeError):
    """Typed Gmail live failure, surfaced after auth/transport problems."""

    def __init__(self, message: str, *, code: str | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class GmailLiveClient:
    """Gmail API client for live ingestion.

    Parameters
    ----------
    credentials_path:
        Path to the OAuth client-secret JSON (``credentials.json`` from Google
        Cloud). Presence is validated on ``authenticate()``.
    token_path:
        Path to the cached user token (``token.json``) produced by the one-time
        consent flow. Refreshed automatically when expired.
    service:
        Optional pre-built Gmail API resource. When supplied the client uses it
        directly and never touches credentials — this is the injection seam for
        unit tests.
    user_id:
        Gmail user id, ``"me"`` for the authenticated user.
    """

    def __init__(
        self,
        credentials_path: Path | None = None,
        token_path: Path | None = None,
        *,
        service: Any | None = None,
        user_id: str = "me",
    ) -> None:
        self._credentials_path = Path(credentials_path) if credentials_path else None
        self._token_path = Path(token_path) if token_path else None
        self._service = service
        self._user_id = user_id

    # -- authentication -----------------------------------------------------

    def authenticate(self) -> None:
        if self._service is not None:
            return
        if self._credentials_path is None:
            raise GmailLiveError("Gmail credentials_path is required for live sync", code="GMAIL_AUTH_FAILURE")
        if not self._credentials_path.exists():
            raise FileNotFoundError(f"Gmail credentials not found: {self._credentials_path}")
        creds = GmailCredentials(credentials_path=self._credentials_path, token_path=self._token_path)
        self._service = load_gmail_service(creds)

    def _svc(self) -> Any:
        if self._service is None:
            self.authenticate()
        return self._service

    # -- fetch --------------------------------------------------------------

    def list_message_ids(self, *, query: str = "", max_results: int = 100) -> list[str]:
        """Return message ids matching ``query`` (Gmail search syntax), newest first."""
        svc = self._svc()
        ids: list[str] = []
        page_token: str | None = None
        try:
            while len(ids) < max_results:
                page_size = min(500, max_results - len(ids))
                resp = (
                    svc.users()
                    .messages()
                    .list(userId=self._user_id, q=query, maxResults=page_size, pageToken=page_token)
                    .execute()
                )
                ids.extend(m["id"] for m in resp.get("messages", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
        except Exception as exc:  # noqa: BLE001 - normalize transport errors
            raise self._wrap(exc, "list_messages") from exc
        return ids[:max_results]

    def get_message(self, message_id: str) -> GmailMessage:
        svc = self._svc()
        try:
            raw = (
                svc.users()
                .messages()
                .get(userId=self._user_id, id=message_id, format="full")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise self._wrap(exc, f"get_message({message_id})") from exc
        return GmailMessage.from_api_message(raw)

    def list_messages(self, *, query: str = "", max_results: int = 100) -> list[GmailMessage]:
        return [self.get_message(mid) for mid in self.list_message_ids(query=query, max_results=max_results)]

    def get_profile_history_id(self) -> str | None:
        """Current mailbox ``historyId`` — the incremental-sync watermark."""
        svc = self._svc()
        try:
            profile = svc.users().getProfile(userId=self._user_id).execute()
        except Exception as exc:  # noqa: BLE001
            raise self._wrap(exc, "getProfile") from exc
        hid = profile.get("historyId")
        return str(hid) if hid is not None else None

    def list_history(self, start_history_id: str, *, max_results: int = 100) -> tuple[list[str], str | None]:
        """Message ids changed since ``start_history_id`` and the new watermark.

        Returns ``(message_ids, latest_history_id)``. Gmail returns a
        ``404`` when ``start_history_id`` is too old to serve — callers should
        fall back to a bounded full resync in that case.
        """
        svc = self._svc()
        message_ids: list[str] = []
        seen: set[str] = set()
        page_token: str | None = None
        latest = start_history_id
        try:
            while True:
                resp = (
                    svc.users()
                    .history()
                    .list(
                        userId=self._user_id,
                        startHistoryId=start_history_id,
                        historyTypes=["messageAdded"],
                        maxResults=min(500, max_results),
                        pageToken=page_token,
                    )
                    .execute()
                )
                latest = str(resp.get("historyId", latest))
                for record in resp.get("history", []):
                    for added in record.get("messagesAdded", []):
                        mid = added.get("message", {}).get("id")
                        if mid and mid not in seen:
                            seen.add(mid)
                            message_ids.append(mid)
                page_token = resp.get("nextPageToken")
                if not page_token or len(message_ids) >= max_results:
                    break
        except Exception as exc:  # noqa: BLE001
            raise self._wrap(exc, "list_history") from exc
        return message_ids[:max_results], latest

    # -- error normalization ------------------------------------------------

    @staticmethod
    def _wrap(exc: Exception, op: str) -> GmailLiveError:
        status = getattr(getattr(exc, "resp", None), "status", None)
        code = "GMAIL_INGESTION_FAILURE"
        retryable = False
        if status is not None:
            status = int(status)
            if status in (401, 403):
                code = "GMAIL_AUTH_FAILURE"
            elif status == 429 or 500 <= status < 600:
                retryable = True
        return GmailLiveError(f"Gmail {op} failed: {exc}", code=code, retryable=retryable)
