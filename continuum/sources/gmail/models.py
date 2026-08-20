"""Gmail source adapter — internal models only."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class GmailParticipant:
    email: str
    name: str | None = None

    @property
    def display(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass
class GmailMessage:
    message_id: str
    thread_id: str
    subject: str
    body: str
    from_participant: GmailParticipant
    to_participants: list[GmailParticipant] = field(default_factory=list)
    cc_participants: list[GmailParticipant] = field(default_factory=list)
    timestamp: str | None = None
    source_url: str | None = None
    attachments: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)

    @property
    def native_source_id(self) -> str:
        return self.message_id

    @classmethod
    def from_api_message(cls, message: dict[str, Any]) -> GmailMessage:
        payload = message.get("payload", {}) or {}
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        from_raw = headers.get("from", "")
        from_participant = _parse_participant(from_raw) or GmailParticipant(email=from_raw or "unknown")

        to_list = [_parse_participant(p) for p in _split_addresses(headers.get("to", ""))]
        cc_list = [_parse_participant(p) for p in _split_addresses(headers.get("cc", ""))]

        # Prefer the decoded MIME body (Gmail format="full"); fall back to the
        # snippet/body fields used by lightweight fixtures.
        body = _extract_body(payload) or str(message.get("snippet") or message.get("body") or "")

        timestamp = headers.get("date") or _internal_date_iso(message.get("internalDate"))
        attachments = list(message.get("attachments") or []) or _extract_attachment_names(payload)

        return cls(
            message_id=message["id"],
            thread_id=message.get("threadId", message["id"]),
            subject=headers.get("subject", "(no subject)"),
            body=body,
            from_participant=from_participant,
            to_participants=[p for p in to_list if p],
            cc_participants=[p for p in cc_list if p],
            timestamp=timestamp,
            source_url=message.get("source_url"),
            attachments=attachments,
            links=list(message.get("links") or []),
        )

    @classmethod
    def from_rfc822_text(cls, *, message_id: str, thread_id: str, text: str) -> GmailMessage:
        """Parse EnterpriseRAG-style RFC822 text fixtures."""
        lines = text.splitlines()
        headers: dict[str, str] = {}
        body_start = 0
        for index, line in enumerate(lines):
            if not line.strip():
                body_start = index + 1
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        from_participant = _parse_participant(headers.get("from", "")) or GmailParticipant(
            email=headers.get("from", "unknown")
        )
        to_list = [_parse_participant(p) for p in _split_addresses(headers.get("to", ""))]
        cc_list = [_parse_participant(p) for p in _split_addresses(headers.get("cc", ""))]
        body = "\n".join(lines[body_start:]).strip()

        return cls(
            message_id=message_id,
            thread_id=thread_id,
            subject=headers.get("subject", "(no subject)"),
            body=body,
            from_participant=from_participant,
            to_participants=[p for p in to_list if p],
            cc_participants=[p for p in cc_list if p],
            timestamp=headers.get("date"),
        )


def _b64url_decode(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")
    except (binascii.Error, ValueError):
        return ""


def _extract_body(payload: dict[str, Any]) -> str:
    """Walk a Gmail payload tree and return the best plaintext body.

    Prefers ``text/plain``; falls back to a naive tag-strip of ``text/html``.
    """
    plain = _find_part_data(payload, "text/plain")
    if plain:
        return plain.strip()
    html = _find_part_data(payload, "text/html")
    if html:
        return _strip_html(html).strip()
    return ""


def _find_part_data(part: dict[str, Any], mime_type: str) -> str:
    if part.get("mimeType") == mime_type:
        data = (part.get("body") or {}).get("data")
        if data:
            return _b64url_decode(data)
    for sub in part.get("parts", []) or []:
        found = _find_part_data(sub, mime_type)
        if found:
            return found
    return ""


def _extract_attachment_names(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        filename = part.get("filename")
        if filename:
            names.append(filename)
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    return names


_HTML_TAG_RE = None


def _strip_html(html: str) -> str:
    global _HTML_TAG_RE
    if _HTML_TAG_RE is None:
        import re

        _HTML_TAG_RE = re.compile(r"<[^>]+>")
    return _HTML_TAG_RE.sub(" ", html)


def _internal_date_iso(internal_date: Any) -> str | None:
    """Gmail ``internalDate`` (epoch millis, as str/int) -> ISO 8601 UTC."""
    if internal_date is None:
        return None
    try:
        millis = int(internal_date)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).replace(microsecond=0).isoformat()


def _split_addresses(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_participant(value: str) -> GmailParticipant | None:
    value = value.strip()
    if not value:
        return None
    if "<" in value and ">" in value:
        name, email = value.split("<", 1)
        return GmailParticipant(name=name.strip().strip('"'), email=email.strip("> ").strip())
    if "@" in value:
        return GmailParticipant(email=value)
    return GmailParticipant(email=value)
