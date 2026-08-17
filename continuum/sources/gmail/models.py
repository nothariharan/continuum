"""Gmail source adapter — internal models only."""

from __future__ import annotations

from dataclasses import dataclass, field
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
        headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
        from_raw = headers.get("from", "")
        from_participant = _parse_participant(from_raw) or GmailParticipant(email=from_raw or "unknown")

        to_list = [_parse_participant(p) for p in _split_addresses(headers.get("to", ""))]
        cc_list = [_parse_participant(p) for p in _split_addresses(headers.get("cc", ""))]

        return cls(
            message_id=message["id"],
            thread_id=message.get("threadId", message["id"]),
            subject=headers.get("subject", "(no subject)"),
            body=str(message.get("snippet") or message.get("body") or ""),
            from_participant=from_participant,
            to_participants=[p for p in to_list if p],
            cc_participants=[p for p in cc_list if p],
            timestamp=headers.get("date"),
            source_url=message.get("source_url"),
            attachments=list(message.get("attachments") or []),
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
