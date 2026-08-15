"""Shared regex patterns for mention and claim extraction."""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
EMAIL_HEADER_RE = re.compile(
    r"^(From|To|Cc|Bcc):\s*(.+)$", re.MULTILINE | re.IGNORECASE
)
EMAIL_NAME_RE = re.compile(r"^(.+?)\s*<([^>]+)>$")
TICKET_RE = re.compile(r"\b([A-Z]{2,5}-\d{1,6})\b")
USERNAME_RE = re.compile(r"(?<![\w.])@([\w.-]{2,64})\b")
PERSON_IN_SLACK_RE = re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?):\s", re.MULTILINE)
FIREflies_SPEAKER_RE = re.compile(
    r"\[(\d{2}:\d{2})\]\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?):", re.MULTILINE
)
GITHUB_REVIEW_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+reviewed\b", re.IGNORECASE
)
OWNS_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:owns|is the owner of|is owner of)\s+(?:the\s+)?([A-Za-z0-9][\w-]{2,60})\b"
)
TAKING_OVER_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:is taking over|taking over)\s+(?:the\s+)?([A-Za-z0-9][\w-]{2,60})\b"
    r"(?:\s+from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?))?"
)
ASSIGNED_TO_RE = re.compile(
    r"(?i:assigned to|assignee:?|owner:?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
)
ASSIGNED_TO_TICKET_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:is assigned to)\s+(.+?)(?:\.|$|\n)"
)
LEADS_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:is leading|leads|is driving|drives)\s+(?:the\s+)?([A-Za-z0-9][\w-]{2,60})\b"
)
BLOCKS_RE = re.compile(
    r"\b(?i:blocks?)\s+([A-Z]{2,5}-\d{1,6})\b"
)
DEPENDS_ON_RE = re.compile(
    r"\b(?i:depends on)\s+([A-Za-z0-9][\w-]{2,60})\b"
)
REVIEWS_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:reviewed|is reviewing)\s+(?:the\s+)?([A-Za-z0-9][\w-]{2,60})\b"
)
OWNER_FIELD_RE = re.compile(
    r"\|\s*([A-Za-z0-9][\w\s\-/]{2,40}?)\s*\|\s*Owner\s*\|", re.IGNORECASE
)
ORG_NAME_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+AI|\s+Tech|\s+Health|\s+Ledger)?)\b"
)
