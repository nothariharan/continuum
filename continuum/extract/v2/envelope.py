"""Evidence envelope: deterministic metadata assembled before any extraction.

The LLM must never rediscover author identity, issue IDs, repositories,
source timestamps, or email addresses that already exist in structured
metadata. This envelope is that structured layer.

The envelope is a frozen dataclass built from the Artifact plus any
resolutions lexicon context; it feeds candidates/relations deterministically
and is also passed to LLM prompts verbatim (so the model sees the same
structured facts the deterministic path used).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from continuum.dataset.artifact import Artifact

TIMELINE_DATE_RE = re.compile(r"^\s*(20[0-9]{2}-[0-9]{2}-[0-9]{2})\s*[-–]", re.MULTILINE)
REVISION_DATE_RE = re.compile(
    r"^\s*[-*]\s*(20[0-9]{2}-[0-9]{2}-[0-9]{2})\s*(?:\(|:)", re.MULTILINE
)
MEETING_DATE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:Meeting:|Date:)\s*(20[0-9]{2}-[0-9]{2}-[0-9]{2})", re.MULTILINE
)


@dataclass(frozen=True)
class EvidenceEnvelope:
    artifact_id: str
    source: str
    title: str | None
    timestamp: str | None
    ts_source: str | None
    author: str | None
    attendees: list[str] = field(default_factory=list)
    subject: str | None = None
    slug: str | None = None
    ticket_ids: list[str] = field(default_factory=list)
    email_from: str | None = None
    email_to: str | None = None
    email_cc: list[str] = field(default_factory=list)
    text_timeline_dates: list[str] = field(default_factory=list)
    revision_dates: list[str] = field(default_factory=list)
    meeting_date: str | None = None
    content: str = field(default_factory=str)

    def to_prompt_dict(self) -> dict[str, Any]:
        """Dict form for LLM prompts: structured facts, no content dump here."""
        return {
            "artifact_id": self.artifact_id,
            "source": self.source,
            "title": self.title,
            "timestamp": self.timestamp,
            "ts_source": self.ts_source,
            "author": self.author,
            "attendees": self.attendees,
            "subject": self.subject,
            "ticket_ids": self.ticket_ids,
            "email_from": self.email_from,
            "email_to": self.email_to,
            "email_cc": self.email_cc,
            "text_timeline_dates": self.text_timeline_dates,
            "revision_dates": self.revision_dates,
            "meeting_date": self.meeting_date,
        }


def _split_names(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def build_envelope(artifact: Artifact) -> EvidenceEnvelope:
    metadata = artifact.metadata or {}
    content = artifact.content or ""
    # Normalize literal backslash-n (double-encoded JSON) so header regexes
    # with ^...$ MULTILINE anchors work on the same text the patterns scan.
    if "\\n" in content:
        content = content.replace("\\n", "\n")
    ticket_ids = re.findall(r"\b([A-Z]{2,5}-\d{1,6})\b", content)

    email_from = email_to = None
    email_cc: list[str] = []
    for line in content.splitlines()[:40]:
        if line.lower().startswith("from:"):
            email_from = line.split(":", 1)[1].strip()
        elif line.lower().startswith("to:"):
            email_to = line.split(":", 1)[1].strip()
        elif line.lower().startswith("cc:"):
            email_cc = _split_names(line.split(":", 1)[1] if ":" in line else None)

    return EvidenceEnvelope(
        artifact_id=artifact.id,
        source=artifact.source,
        title=artifact.title,
        timestamp=artifact.timestamp,
        ts_source=metadata.get("ts_source"),
        author=artifact.author,
        attendees=_split_names(metadata.get("attendees")),
        subject=metadata.get("subject") or (artifact.title if artifact.source == "gmail" else None),
        slug=metadata.get("slug"),
        ticket_ids=ticket_ids,
        email_from=email_from,
        email_to=email_to,
        email_cc=email_cc,
        text_timeline_dates=[m.group(1) for m in TIMELINE_DATE_RE.finditer(content)],
        revision_dates=[m.group(1) for m in REVISION_DATE_RE.finditer(content)],
        meeting_date=(m.group(1) if (m := MEETING_DATE_RE.search(content)) else None),
        content=content,
    )
