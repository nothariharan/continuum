"""Normalize Gmail messages to canonical Artifacts."""

from __future__ import annotations

import re
from email.utils import parsedate_to_datetime

from continuum.dataset.artifact import SOURCE_TYPE, Artifact
from continuum.sources.provenance import gmail_source_url, utc_now_iso

from .models import GmailMessage, GmailParticipant

LINK_RE = re.compile(r"https?://[^\s<>]+")


def _parse_timestamp(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).isoformat()
    except (ValueError, TypeError, IndexError):
        match = re.search(r"([0-9]{4}-[0-9]{2}-[0-9]{2})", raw)
        return f"{match.group(1)}T00:00:00" if match else raw


def _participant_dict(participant: GmailParticipant) -> dict[str, str]:
    return {"email": participant.email, "display_name": participant.display}


def _collect_participants(message: GmailMessage) -> list[dict[str, str]]:
    seen: set[str] = set()
    participants: list[dict[str, str]] = []

    def add(participant: GmailParticipant) -> None:
        key = participant.email.lower()
        if key in seen:
            return
        seen.add(key)
        participants.append(_participant_dict(participant))

    add(message.from_participant)
    for participant in message.to_participants + message.cc_participants:
        add(participant)
    return participants


def build_content(message: GmailMessage) -> str:
    lines = [
        f"From: {message.from_participant.display}",
    ]
    if message.to_participants:
        lines.append(f"To: {', '.join(p.display for p in message.to_participants)}")
    if message.cc_participants:
        lines.append(f"Cc: {', '.join(p.display for p in message.cc_participants)}")
    if message.timestamp:
        lines.append(f"Date: {message.timestamp}")
    lines.append(f"Subject: {message.subject}")
    lines.append("")
    lines.append(message.body)
    return "\n".join(lines)


def normalize_gmail_message(message: GmailMessage, *, ingested_at: str | None = None) -> Artifact:
    ingested_at = ingested_at or utc_now_iso()
    links = list(message.links)
    links.extend(LINK_RE.findall(message.body))
    links = list(dict.fromkeys(links))

    metadata = {
        "message_id": message.message_id,
        "thread_id": message.thread_id,
        "subject": message.subject,
        "participants": _collect_participants(message),
        "attachments": message.attachments,
        "links": links,
        "source_url": message.source_url or gmail_source_url(message.message_id),
        "ingested_at": ingested_at,
    }

    return Artifact.from_source_record(
        source="gmail",
        native_source_id=message.native_source_id,
        type=SOURCE_TYPE["gmail"],
        content=build_content(message),
        author=message.from_participant.display,
        timestamp=_parse_timestamp(message.timestamp),
        title=message.subject,
        metadata=metadata,
    )
