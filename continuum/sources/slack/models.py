"""Slack source adapter — internal models only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SlackUser:
    id: str
    name: str
    real_name: str | None = None
    profile: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.real_name or self.profile.get("display_name") or self.name


@dataclass
class SlackMessage:
    ts: str
    channel_id: str
    channel_name: str
    text: str
    user_id: str | None = None
    user_display: str | None = None
    thread_ts: str | None = None
    reply_count: int = 0
    workspace_id: str = "T00000000"
    workspace_subdomain: str = "redwood-acme"
    permalink: str | None = None
    replies: list[SlackMessage] = field(default_factory=list)

    @property
    def native_source_id(self) -> str:
        return f"{self.channel_id}:{self.ts}"

    @classmethod
    def from_api_message(
        cls,
        message: dict[str, Any],
        *,
        channel_id: str,
        channel_name: str,
        workspace_id: str = "T00000000",
        workspace_subdomain: str = "redwood-acme",
        users: dict[str, SlackUser] | None = None,
    ) -> SlackMessage:
        users = users or {}
        user_id = message.get("user")
        user_display = None
        if user_id and user_id in users:
            user_display = users[user_id].display_name
        elif message.get("username"):
            user_display = message["username"]

        return cls(
            ts=str(message["ts"]),
            channel_id=channel_id,
            channel_name=channel_name,
            text=str(message.get("text") or ""),
            user_id=user_id,
            user_display=user_display,
            thread_ts=message.get("thread_ts"),
            reply_count=int(message.get("reply_count") or 0),
            workspace_id=workspace_id,
            workspace_subdomain=workspace_subdomain,
            permalink=message.get("permalink"),
        )


@dataclass
class SlackThreadFixture:
    """Recorded conversations.history + conversations.replies fixture."""

    channel_id: str
    channel_name: str
    workspace_id: str
    workspace_subdomain: str
    messages: list[dict[str, Any]]
    replies: dict[str, list[dict[str, Any]]]
    users: dict[str, dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlackThreadFixture:
        return cls(
            channel_id=data["channel_id"],
            channel_name=data["channel_name"],
            workspace_id=data.get("workspace_id", "T00000000"),
            workspace_subdomain=data.get("workspace_subdomain", "redwood-acme"),
            messages=list(data.get("messages") or []),
            replies={k: list(v) for k, v in (data.get("replies") or {}).items()},
            users=dict(data.get("users") or {}),
        )

    def to_messages(self) -> list[SlackMessage]:
        users = {
            uid: SlackUser(
                id=uid,
                name=u.get("name", uid),
                real_name=u.get("real_name"),
                profile=u.get("profile") or {},
            )
            for uid, u in self.users.items()
        }
        result: list[SlackMessage] = []
        for raw in self.messages:
            msg = SlackMessage.from_api_message(
                raw,
                channel_id=self.channel_id,
                channel_name=self.channel_name,
                workspace_id=self.workspace_id,
                workspace_subdomain=self.workspace_subdomain,
                users=users,
            )
            reply_raw = self.replies.get(msg.ts, [])
            msg.replies = [
                SlackMessage.from_api_message(
                    r,
                    channel_id=self.channel_id,
                    channel_name=self.channel_name,
                    workspace_id=self.workspace_id,
                    workspace_subdomain=self.workspace_subdomain,
                    users=users,
                )
                for r in reply_raw
            ]
            result.append(msg)
        return result
