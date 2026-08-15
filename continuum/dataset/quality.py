"""Data-quality report over the normalized Phase 2A sample."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"\b(\+?\d[\d\s().-]{8,}\d)\b")
TICKET_RE = re.compile(r"\b([A-Z]{2,5}-\d{1,6})\b")
GITHUB_RE = re.compile(r"\b(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?(?:#\d{2,6}|PR-\d{3,6})\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+|www\.\S+")
DSID_RE = re.compile(r"\bdsid_[0-9a-f]{32}\b")


@dataclass
class SourceQuality:
    source: str
    records: int
    with_title: int
    with_author: int
    with_timestamp: int
    ts_header: int
    ts_slug: int
    with_ticket_refs: int
    ticket_refs: int
    emails: int
    urls: int
    noise_docs: int
    sample_docs: int
    title_bytes: int
    min_len: int
    max_len: int


@dataclass
class QualityReport:
    total_records: int
    rejected: int
    source_stats: list[SourceQuality]
    total_emails: int
    total_tickets: int
    total_urls: int


def quality_report(records: list[dict], rejected: list[dict], scan_cap: int = 400) -> QualityReport:
    sources: dict[str, dict] = {}
    order: list[str] = []
    total_emails = total_tickets = total_urls = 0
    for record in records[:scan_cap]:
        source = record["source"]
        if source not in sources:
            sources[source] = {
                "source": source,
                "records": 0,
                "with_title": 0,
                "with_author": 0,
                "with_timestamp": 0,
                "ts_header": 0,
                "ts_slug": 0,
                "with_ticket_refs": 0,
                "ticket_refs": 0,
                "emails": 0,
                "urls": 0,
                "noise_docs": 0,
                "sample_docs": 0,
                "title_bytes": 0,
                "min_len": None,
                "max_len": 0,
            }
            order.append(source)
        stats = sources[source]
        content = record["content"]
        stats["records"] += 1
        if record["title"]:
            stats["with_title"] += 1
            stats["title_bytes"] += len(record["title"])
        if record["author"]:
            stats["with_author"] += 1
        if record["timestamp"]:
            stats["with_timestamp"] += 1
            ts_source = (record.get("metadata") or {}).get("ts_source")
            if ts_source == "header":
                stats["ts_header"] += 1
            elif ts_source:
                stats["ts_slug"] += 1
        emails = len(EMAIL_RE.findall(content))
        tickets = len(TICKET_RE.findall(content))
        urls = len(URL_RE.findall(content))
        stats["emails"] += emails
        stats["ticket_refs"] += tickets
        stats["urls"] += urls
        if tickets:
            stats["with_ticket_refs"] += 1
        if (record.get("metadata") or {}).get("noise"):
            stats["noise_docs"] += 1
        n = len(content)
        stats["min_len"] = n if stats["min_len"] is None else min(stats["min_len"], n)
        stats["max_len"] = max(stats["max_len"], n)
        total_emails += emails
        total_tickets += tickets
        total_urls += urls

    for source in order:
        stats = sources[source]
        if stats["min_len"] is None:
            stats["min_len"] = 0
    source_stats = [SourceQuality(**sources[s]) for s in order]
    return QualityReport(
        total_records=len(records),
        rejected=len(rejected),
        source_stats=source_stats,
        total_emails=total_emails,
        total_tickets=total_tickets,
        total_urls=total_urls,
    )


def quality_to_dict(report: QualityReport) -> dict:
    return asdict(report)