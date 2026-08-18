"""Normalize Slack messages to canonical Artifacts."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from continuum.dataset.artifact import SOURCE_TYPE, Artifact
from continuum.sources.provenance import slack_permalink, utc_now_iso

from .models import SlackMessage

MENTION_RE = re.compile(r"<@([A-Z0-9]+)>|@([a-zA-Z0-9._-]+)")
LINK_RE = re.compile(r"https?://[^\s<>]+")


def slack_ts_to_iso(ts: str) -> str:
    try:
        seconds = float(ts)
        return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(microsecond=0).isoformat()
    except (ValueError, OSError, OverflowError):
        return ts


def extract_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    for match in MENTION_RE.finditer(text):
        value = match.group(1) or match.group(2)
        if value and value not in mentions:
            mentions.append(value if match.group(2) else f"<@{value}>")
    return mentions


def extract_links(text: str) -> list[str]:
    return LINK_RE.findall(text)


def build_content(message: SlackMessage) -> str:
    """Conversational text shape compatible with existing slack extraction."""
    lines: list[str] = []
    header = message.channel_name or message.channel_id
    lines.append(f"#{header.lstrip('#')}")

    def append_line(msg: SlackMessage, *, prefix: str = "") -> None:
        author = msg.user_display or msg.user_id or "unknown"
        body = msg.text.strip()
        if body:
            lines.append(f"{prefix}{author}: {body}")

    append_line(message)
    for reply in message.replies:
        append_line(reply, prefix="  ")

    return "\n".join(lines)


def collect_participants(message: SlackMessage) -> list[dict[str, str]]:
    seen: set[str] = set()
    participants: list[dict[str, str]] = []

    def add(msg: SlackMessage) -> None:
        if not msg.user_id or msg.user_id in seen:
            return
        seen.add(msg.user_id)
        participant = {
            "user_id": msg.user_id,
            "display_name": msg.user_display or msg.user_id,
        }
        if msg.username:
            participant["username"] = msg.username
        participants.append(participant)

    add(message)
    for reply in message.replies:
        add(reply)
    return participants


def normalize_slack_message(message: SlackMessage, *, ingested_at: str | None = None) -> Artifact:
    ingested_at = ingested_at or utc_now_iso()
    thread_id = message.thread_ts or (message.ts if message.replies else None)
    source_url = message.permalink
    if not source_url:
        source_url = slack_permalink(
            message.workspace_subdomain,
            message.channel_id,
            message.ts,
        )

    metadata = {
        "message_id": message.ts,
        "channel_id": message.channel_id,
        "channel_name": message.channel_name,
        "thread_id": thread_id,
        "workspace_id": message.workspace_id,
        "author_user_id": message.user_id,
        "author_display_name": message.user_display,
        "participants": collect_participants(message),
        "mentions": extract_mentions(message.text),
        "links": extract_links(message.text),
        "reply_count": message.reply_count or len(message.replies),
        "source_url": source_url,
        "ingested_at": ingested_at,
    }
    if message.replies:
        for reply in message.replies:
            metadata["mentions"] = list(
                dict.fromkeys(metadata["mentions"] + extract_mentions(reply.text))
            )
            metadata["links"] = list(dict.fromkeys(metadata["links"] + extract_links(reply.text)))

    title = f"#{message.channel_name.lstrip('#')}"
    author = message.user_display

    return Artifact.from_source_record(
        source="slack",
        native_source_id=message.native_source_id,
        type=SOURCE_TYPE["slack"],
        content=build_content(message),
        author=author,
        timestamp=slack_ts_to_iso(message.ts),
        title=title,
        metadata=metadata,
    )
