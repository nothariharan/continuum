"""Corpus inventory read directly from the pinned archive (no extraction)."""

from __future__ import annotations

import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

DSID_RE = re.compile(r"^dsid_([0-9a-f]{32})__")
EMAIL_DATE_RE = re.compile(r"Date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
EMAIL_FROM_RE = re.compile(r"From:\s*[^\n]+<[^>]+>")
MEETING_DATE_RE = re.compile(r"^Date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.MULTILINE)
GENERIC_DATE_RE = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})T[0-9]{2}:")

SOURCES = (
    "slack",
    "gmail",
    "linear",
    "google_drive",
    "hubspot",
    "fireflies",
    "github",
    "jira",
    "confluence",
)


@dataclass
class SourceInventory:
    source: str
    file_count: int
    total_bytes: int
    min_bytes: int
    max_bytes: int
    sample_dsids: list[str]


@dataclass
class CorpusInventory:
    manifest_release: str
    total_files: int
    total_bytes: int
    sources: list[SourceInventory]
    scanned_docs: int
    observed_email_dates: int
    observed_meeting_dates: int
    observed_dates_anywhere: int
    observed_noise_flags: int


def inventory_corpus(archive: zipfile.ZipFile, scan_cap: int = 600) -> CorpusInventory:
    names = [n for n in archive.namelist() if not n.endswith("/")]
    sources = []
    for source in SOURCES:
        prefix = f"{source}/"
        files = [n for n in names if n.startswith(prefix)]
        if not files:
            continue
        sizes = []
        sample = []
        for name in files[:6]:
            info = archive.getinfo(name)
            sizes.append(info.file_size)
            match = DSID_RE.match(name.rsplit("/", 1)[-1])
            if match:
                sample.append(match.group(1))
        all_sizes = [archive.getinfo(n).file_size for n in files]
        sources.append(
            SourceInventory(
                source=source,
                file_count=len(files),
                total_bytes=sum(all_sizes),
                min_bytes=min(all_sizes),
                max_bytes=max(all_sizes),
                sample_dsids=sample,
            )
        )

    email_dates = 0
    meeting_dates = 0
    dates = 0
    noise = 0
    scanned = 0
    per_source_cap = max(1, scan_cap // max(1, len(SOURCES)))
    for source in SOURCES:
        prefix = f"{source}/"
        source_files = [n for n in names if n.startswith(prefix)][:per_source_cap]
        for name in source_files:
            info = archive.getinfo(name)
            if info.file_size > 200_000:
                continue
            text = archive.read(name).decode("utf-8", errors="replace")[:6000]
            scanned += 1
            if EMAIL_FROM_RE.search(text) and EMAIL_DATE_RE.search(text):
                email_dates += 1
            if MEETING_DATE_RE.search(text):
                meeting_dates += 1
            if GENERIC_DATE_RE.search(text) or EMAIL_DATE_RE.search(text):
                dates += 1
            if "dataset_noise_document" in text:
                noise += 1

    return CorpusInventory(
        manifest_release="v1.0.0",
        total_files=len(names),
        total_bytes=sum(archive.getinfo(n).file_size for n in names),
        sources=sources,
        scanned_docs=scanned,
        observed_email_dates=email_dates,
        observed_meeting_dates=meeting_dates,
        observed_dates_anywhere=dates,
        observed_noise_flags=noise,
    )


def inventory_to_dict(inventory: CorpusInventory) -> dict:
    return asdict(inventory)