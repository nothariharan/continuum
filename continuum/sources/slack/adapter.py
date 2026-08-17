"""Slack source connector — fixtures-first, live API stub for later."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from continuum.dataset.artifact import Artifact
from continuum.sources.connector import FetchResult
from continuum.sources.cursor import SyncCursor
from continuum.sources.provenance import utc_now_iso

from .models import SlackMessage, SlackThreadFixture
from .normalize import normalize_slack_message

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
    ) -> None:
        self._fixtures_dir = fixtures_dir or DEFAULT_FIXTURES
        self._token = token
        self._fixture_messages: list[SlackMessage] | None = None

    def authenticate(self) -> None:
        if self._token:
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

    def fetch(self, *, cursor: SyncCursor | None = None, limit: int = 100) -> FetchResult:
        self.authenticate()
        if self._token:
            raise NotImplementedError("Live Slack API fetch requires SLACK_BOT_TOKEN wiring")
        all_messages = self._load_fixtures()
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
