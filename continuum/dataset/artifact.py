"""Canonical Artifact model and deterministic raw -> Artifact normalization."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .manifest import SOURCE_ALIASES

DSID_RE = re.compile(r"^dsid_([0-9a-f]{32})__")
SLUG_RE = re.compile(r"^dsid_[0-9a-f]{32}__(.+)\.txt$")

EMAIL_FROM_RE = re.compile(r"^From:\s*(.+)$", re.MULTILINE)
EMAIL_DATE_RE = re.compile(r"^Date:\s*(.+)$", re.MULTILINE)
EMAIL_SUBJECT_RE = re.compile(r"^Subject:\s*(.+)$", re.MULTILINE)
MEETING_DATE_RE = re.compile(r"^Date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.MULTILINE)
MEETING_ATTENDEES_RE = re.compile(r"^Attendees:\s*(.+)$", re.MULTILINE)
UNIX_TS_SLUG_RE = re.compile(r"^([0-9]{9,10})[-_]")
DATE_SLUG_RE = re.compile(r"^(20[0-9]{2})-?([0-9]{2})?-?([0-9]{2})?[-_]")
TICKET_SLUG_RE = re.compile(r"^([A-Z]+-[0-9]+)")

SOURCE_TYPE = {
    "slack": "slack_message",
    "gmail": "gmail_message",
    "linear": "linear_ticket",
    "google_drive": "google_drive_document",
    "hubspot": "hubspot_crm_record",
    "fireflies": "meeting_transcript",
    "github": "github_pr",
    "jira": "jira_ticket",
    "confluence": "confluence_page",
}


@dataclass(frozen=True)
class Artifact:
    id: str
    source: str
    source_id: str
    type: str
    author: str | None
    timestamp: str | None
    title: str | None
    content: str
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_raw(cls, source: str, path: str, text: str) -> "Artifact":
        name = path.rsplit("/", 1)[-1]
        dsid_match = DSID_RE.match(name)
        slug_match = SLUG_RE.match(name)
        if source not in SOURCE_ALIASES or dsid_match is None:
            raise ValueError(f"unrecognized raw document: {path}")
        dsid = dsid_match.group(1)
        slug = slug_match.group(1) if slug_match else None

        author = timestamp = title = None
        metadata = {}
        if "dataset_noise_document" in text:
            metadata["noise"] = True

        first_line = text.splitlines()[0].strip() if text else None

        if source == "gmail":
            author, subject, timestamp = _extract_gmail(text)
            title = subject or first_line or slug
            if title:
                metadata["subject"] = title
            if timestamp is None:
                timestamp = _slug_timestamp(slug)
        elif source == "fireflies":
            attendees, ts = _extract_meeting(text)
            if attendees:
                metadata["attendees"] = attendees
            timestamp = ts or _slug_timestamp(slug)
            title = first_line or slug
        else:
            title = first_line or slug
            timestamp = _slug_timestamp(slug)
        if title:
            metadata["slug"] = slug
        if timestamp:
            metadata["ts_source"] = _ts_source(timestamp, slug, text)

        return cls(
            id=f"dsid_{dsid}",
            source=source,
            source_id=dsid,
            type=SOURCE_TYPE[source],
            author=author,
            timestamp=timestamp,
            title=title,
            content=text,
            metadata=metadata,
        )


def _slug_timestamp(slug: str | None) -> str | None:
    if not slug:
        return None
    m = UNIX_TS_SLUG_RE.match(slug)
    if m:
        try:
            return datetime.fromtimestamp(int(m.group(1))).isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    m = DATE_SLUG_RE.match(slug)
    if m:
        year, month, day = m.group(1), m.group(2), m.group(3)
        if month and day:
            return f"{year}-{month}-{day}T00:00:00"
        if month:
            return f"{year}-{month}-01T00:00:00"
        return f"{year}-01-01T00:00:00"
    return None


def _ts_source(timestamp: str | None, slug: str | None, text: str) -> str | None:
    if not timestamp:
        return None
    if EMAIL_DATE_RE.search(text) or MEETING_DATE_RE.search(text):
        return "header"
    if UNIX_TS_SLUG_RE.match(slug or ""):
        return "unix-slug"
    if DATE_SLUG_RE.match(slug or ""):
        return "date-slug"
    return None


def _parse_iso(value: str) -> str | None:
    value = value.strip()
    match = re.search(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?:T[0-9:]{2}(?::[0-9]{2})?)?(?:Z)?", value)
    if not match:
        return None
    try:
        return datetime.fromisoformat(match.group(0).replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _extract_gmail(text: str) -> tuple[str | None, str | None, str | None]:
    author = subject = timestamp = None
    m_from = EMAIL_FROM_RE.search(text)
    m_subject = EMAIL_SUBJECT_RE.search(text)
    m_date = EMAIL_DATE_RE.search(text)
    if m_from:
        author = m_from.group(1).strip()
    if m_subject:
        subject = m_subject.group(1).strip()
    if m_date:
        timestamp = _parse_iso(m_date.group(1))
    return author, subject, timestamp


def _extract_meeting(text: str) -> tuple[str | None, str | None]:
    attendees = None
    m = MEETING_ATTENDEES_RE.search(text)
    if m:
        attendees = ", ".join(m.group(1).split(", "))
    m_date = MEETING_DATE_RE.search(text)
    timestamp = _parse_iso(m_date.group(1)) if m_date else None
    return attendees, timestamp


def normalize_artifact(path: Path) -> Artifact:
    source = path.parent.name
    text = path.read_text(encoding="utf-8", errors="replace")
    return Artifact.from_raw(source=source, path=path.name, text=text)


def normalize_many(files: list[Path]) -> list[Artifact]:
    artifacts = []
    for path in files:
        try:
            artifacts.append(normalize_artifact(path))
        except (ValueError, OSError):
            continue
    return artifacts


def artifact_to_dict(artifact: Artifact) -> dict:
    return asdict(artifact)