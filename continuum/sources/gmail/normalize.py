"""Normalize Gmail messages to canonical Artifacts."""

from __future__ import annotations

import re
from email.utils import parsedate_to_datetime

from continuum.dataset.artifact import SOURCE_TYPE, Artifact
from continuum.sources.provenance import gmail_source_url, utc_now_iso

from .models import GmailMessage, GmailParticipant

LINK_RE = re.compile(r"https?://[^\s<>]+")

# Boundaries where new email text ends and quoted history begins. Conservative
# on purpose: a false split would drop real content, so we only cut on strong,
# unambiguous markers.
_QUOTE_MARKERS = (
    re.compile(r"^On .+ wrote:\s*$", re.IGNORECASE),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}", re.IGNORECASE),
    re.compile(r"^_{5,}\s*$"),
    re.compile(r"^From:\s.+", re.IGNORECASE),  # forwarded/replied header block
)


def split_new_and_quoted(body: str) -> tuple[str, str]:
    """Split an email body into (new_text, quoted_text).

    The new text is everything before the first quote boundary or leading ``>``
    block. Quoted history is preserved separately so provenance is not lost, but
    it is kept out of the text the extractor reasons over.
    """
    lines = body.splitlines()
    cut = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(">"):
            cut = index
            break
        if any(marker.match(stripped) for marker in _QUOTE_MARKERS):
            cut = index
            break
    if cut is None:
        return body, ""
    new_text = "\n".join(lines[:cut]).strip()
    quoted = "\n".join(lines[cut:]).strip()
    # Guard against over-eager splits that would leave no new content.
    if not new_text:
        return body, ""
    return new_text, quoted


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


def build_content(message: GmailMessage, *, body: str | None = None) -> str:
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
    lines.append(message.body if body is None else body)
    return "\n".join(lines)


def normalize_gmail_message(message: GmailMessage, *, ingested_at: str | None = None) -> Artifact:
    ingested_at = ingested_at or utc_now_iso()
    new_body, quoted_body = split_new_and_quoted(message.body)
    # Links are collected from the new text only — quoted history is not a new event.
    links = list(message.links)
    links.extend(LINK_RE.findall(new_body))
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
    if quoted_body:
        metadata["quoted_excerpt"] = quoted_body[:2000]
        metadata["has_quoted_history"] = True

    return Artifact.from_source_record(
        source="gmail",
        native_source_id=message.native_source_id,
        type=SOURCE_TYPE["gmail"],
        content=build_content(message, body=new_body),
        author=message.from_participant.display,
        timestamp=_parse_timestamp(message.timestamp),
        title=message.subject,
        metadata=metadata,
    )
