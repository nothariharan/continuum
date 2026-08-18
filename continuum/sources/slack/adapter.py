"""Slack source connector — fixtures-first, live API when token configured."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from continuum.dataset.artifact import Artifact
from continuum.sources.connector import FetchResult
from continuum.sources.cursor import SyncCursor
from continuum.sources.provenance import utc_now_iso

from .live import SlackWebClient
from .models import SlackMessage, SlackThreadFixture
from .normalize import normalize_slack_message
from .oauth import SlackCredentials

DEFAULT_FIXTURES = (
    Path(__file__).resolve().parents[3] / "data" / "fixtures" / "sources" / "slack"
)


class SlackAdapter:
    source = "slack"

    def __init__(
        self,
        *,
        fixtures_dir: Path | None = None,
        token: str | None = None,
        channel_ids: list[str] | None = None,
    ) -> None:
        self._fixtures_dir = fixtures_dir or DEFAULT_FIXTURES
        self._token = token
        self._channel_ids = channel_ids or _channel_ids_from_env()
        self._fixture_messages: list[SlackMessage] | None = None
        self._live_messages: list[SlackMessage] | None = None
        self._client: SlackWebClient | None = None

    def authenticate(self) -> None:
        if self._token:
            self._client = SlackWebClient(self._token)
            auth = self._client.auth_test()
            self._workspace_id = str(auth.get("team_id") or "T00000000")
            self._workspace_subdomain = str(auth.get("url", "https://slack.com").split("//")[1].split(".")[0])
            return
        if not self._fixtures_dir.is_dir():
            raise FileNotFoundError(f"Slack fixtures dir not found: {self._fixtures_dir}")

    def _load_fixtures(self) -> list[SlackMessage]:
        if self._fixture_messages is not None:
            return self._fixture_messages
        messages: list[SlackMessage] = []
        for path in sorted(self._fixtures_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            fixture = SlackThreadFixture.from_dict(data)
            messages.extend(fixture.to_messages())
        self._fixture_messages = messages
        return messages

    def _load_live(self) -> list[SlackMessage]:
        if self._live_messages is not None:
            return self._live_messages
        assert self._client is not None
        messages: list[SlackMessage] = []
        for channel_id in self._channel_ids:
            resp = self._client.conversations_history(channel_id, limit=200)
            channel_name = channel_id
            users: dict[str, dict[str, Any]] = {}
            for raw in resp.get("messages", []):
                user_id = raw.get("user")
                if user_id and user_id not in users:
                    try:
                        users[user_id] = self._client.users_info(user_id).get("user", {})
                    except RuntimeError:
                        users[user_id] = {"id": user_id, "name": user_id}
                msg = self._client.message_from_api(
                    raw,
                    channel_id=channel_id,
                    channel_name=channel_name,
                    workspace_id=getattr(self, "_workspace_id", "T00000000"),
                    workspace_subdomain=getattr(self, "_workspace_subdomain", "workspace"),
                    users=users,
                )
                messages.append(msg)
        self._live_messages = sorted(messages, key=lambda m: m.ts)
        return self._live_messages

    def fetch_record(self, native_id: str) -> SlackMessage | None:
        pool = self._load_live() if self._token else self._load_fixtures()
        for msg in pool:
            if msg.native_source_id == native_id:
                return msg
        return None

    def fetch(self, *, cursor: SyncCursor | None = None, limit: int = 100) -> FetchResult:
        self.authenticate()
        all_messages = self._load_live() if self._token else self._load_fixtures()
        start = 0
        if cursor is not None:
            for index, msg in enumerate(all_messages):
                if msg.native_source_id == cursor.value:
                    start = index + 1
                    break
        batch = all_messages[start : start + limit]
        next_cursor = None
        if start + limit < len(all_messages) and batch:
            next_cursor = self.cursor(batch[-1])
        return FetchResult(records=batch, next_cursor=next_cursor)

    def normalize(self, raw: Any) -> Artifact:
        if not isinstance(raw, SlackMessage):
            raise TypeError(f"expected SlackMessage, got {type(raw)}")
        return normalize_slack_message(raw)

    def cursor(self, raw: Any) -> SyncCursor:
        if not isinstance(raw, SlackMessage):
            raise TypeError(f"expected SlackMessage, got {type(raw)}")
        return SyncCursor(source=self.source, value=raw.native_source_id, last_sync_at=utc_now_iso())

    def provenance(self, raw: Any) -> dict[str, Any]:
        artifact = self.normalize(raw)
        return {
            "source": self.source,
            "source_id": artifact.source_id,
            "source_url": artifact.metadata.get("source_url"),
            "ingested_at": artifact.metadata.get("ingested_at"),
        }

    def normalize_all_fixtures(self) -> list[Artifact]:
        return [self.normalize(msg) for msg in self._load_fixtures()]


def _channel_ids_from_env() -> list[str]:
    raw = os.environ.get("SLACK_CHANNEL_IDS", "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def adapter_from_env(*, fixtures_dir: Path | None = None) -> SlackAdapter:
    token = os.environ.get("SLACK_BOT_TOKEN")
    if token:
        SlackCredentials.from_env()
    return SlackAdapter(fixtures_dir=fixtures_dir, token=token)
