"""Deterministic source-metadata mention and claim extraction."""

from __future__ import annotations

import re
from typing import Protocol

from continuum.dataset.artifact import Artifact

from .patterns import (
    ASSIGNED_TO_RE,
    ASSIGNED_TO_TICKET_RE,
    BLOCKS_RE,
    DEPENDS_ON_RE,
    EMAIL_HEADER_RE,
    EMAIL_NAME_RE,
    EMAIL_RE,
    FIREflies_SPEAKER_RE,
    LEADS_RE,
    OWNS_RE,
    PERSON_IN_SLACK_RE,
    REVIEWS_RE,
    TAKING_OVER_RE,
    TICKET_RE,
    USERNAME_RE,
)
from .schemas import Claim, Mention

MIN_CLAIM_CONFIDENCE = 0.70
BLOCKED_MENTIONS = frozenset(
    {
        "she",
        "he",
        "they",
        "we",
        "our",
        "their",
        "his",
        "her",
        "it",
        "this",
        "that",
        "team",
        "owner",
        "purpose",
        "action",
        "typical initial role",
        "widget",
        "description",
    }
)


def _valid_entity(text: str) -> bool:
    value = text.strip()
    if len(value) < 3:
        return False
    if value.lower() in BLOCKED_MENTIONS:
        return False
    if value.lower() in {"the", "and", "for", "with"}:
        return False
    return True


class MentionExtractor(Protocol):
    def extract(self, artifact: Artifact) -> list[Mention]: ...


class DeterministicMentionExtractor:
    """Extract mentions using source-aware regex and header parsing."""

    def extract(self, artifact: Artifact) -> list[Mention]:
        extractors = {
            "gmail": self._extract_gmail,
            "slack": self._extract_slack,
            "linear": self._extract_linear,
            "jira": self._extract_jira,
            "github": self._extract_github,
            "fireflies": self._extract_fireflies,
            "hubspot": self._extract_hubspot,
            "confluence": self._extract_confluence,
            "google_drive": self._extract_generic,
        }
        handler = extractors.get(artifact.source, self._extract_generic)
        mentions = handler(artifact)
        return _dedupe_mentions(mentions)

    def _extract_gmail(self, artifact: Artifact) -> list[Mention]:
        mentions: list[Mention] = []
        content = artifact.content
        for match in EMAIL_HEADER_RE.finditer(content):
            header = match.group(1).lower()
            value = match.group(2).strip()
            for part in re.split(r",\s*", value):
                part = part.strip()
                if not part:
                    continue
                name_match = EMAIL_NAME_RE.match(part)
                if name_match:
                    name, email = name_match.group(1).strip(), name_match.group(2).strip()
                    mentions.append(
                        Mention.create(
                            artifact_id=artifact.id,
                            source=artifact.source,
                            raw_text=name,
                            type="person",
                            content=content,
                            span_start=match.start(),
                            span_end=match.end(),
                            source_identity=email,
                            confidence=0.95,
                        )
                    )
                    mentions.append(
                        Mention.create(
                            artifact_id=artifact.id,
                            source=artifact.source,
                            raw_text=email,
                            type="email",
                            content=content,
                            span_start=match.start(),
                            span_end=match.end(),
                            source_identity=email,
                            confidence=0.98,
                        )
                    )
                elif EMAIL_RE.match(part):
                    mentions.append(
                        Mention.create(
                            artifact_id=artifact.id,
                            source=artifact.source,
                            raw_text=part,
                            type="email",
                            content=content,
                            span_start=match.start(),
                            span_end=match.end(),
                            source_identity=part,
                            confidence=0.98,
                        )
                    )
                elif header == "from":
                    mentions.append(
                        Mention.create(
                            artifact_id=artifact.id,
                            source=artifact.source,
                            raw_text=part,
                            type="person",
                            content=content,
                            span_start=match.start(),
                            span_end=match.end(),
                            confidence=0.90,
                        )
                    )
        mentions.extend(self._extract_tickets(artifact))
        mentions.extend(self._extract_emails_in_body(artifact))
        return mentions

    def _extract_slack(self, artifact: Artifact) -> list[Mention]:
        mentions: list[Mention] = []
        content = artifact.content
        for match in PERSON_IN_SLACK_RE.finditer(content):
            name = match.group(1).strip()
            mentions.append(
                Mention.create(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    raw_text=name,
                    type="person",
                    content=content,
                    span_start=match.start(1),
                    span_end=match.end(1),
                    confidence=0.88,
                )
            )
        for match in USERNAME_RE.finditer(content):
            handle = f"@{match.group(1)}"
            mentions.append(
                Mention.create(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    raw_text=handle,
                    type="username",
                    content=content,
                    span_start=match.start(),
                    span_end=match.end(),
                    source_identity=handle,
                    confidence=0.92,
                )
            )
        mentions.extend(self._extract_tickets(artifact))
        mentions.extend(self._extract_emails_in_body(artifact))
        return mentions

    def _extract_linear(self, artifact: Artifact) -> list[Mention]:
        mentions = self._extract_generic(artifact)
        content = artifact.content
        title = artifact.title or ""
        if title:
            ticket_match = re.match(r"^([a-z0-9-]+)$", title)
            if ticket_match:
                mentions.append(
                    Mention.create(
                        artifact_id=artifact.id,
                        source=artifact.source,
                        raw_text=title,
                        type="project",
                        content=content,
                        span_start=0,
                        span_end=len(title),
                        confidence=0.85,
                    )
                )
        return mentions

    def _extract_jira(self, artifact: Artifact) -> list[Mention]:
        return self._extract_linear(artifact)

    def _extract_github(self, artifact: Artifact) -> list[Mention]:
        mentions = self._extract_generic(artifact)
        content = artifact.content
        title = artifact.title or ""
        if title:
            mentions.append(
                Mention.create(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    raw_text=title,
                    type="project",
                    content=content,
                    span_start=0,
                    span_end=min(len(title), len(content)),
                    confidence=0.80,
                )
            )
        return mentions

    def _extract_fireflies(self, artifact: Artifact) -> list[Mention]:
        mentions: list[Mention] = []
        content = artifact.content
        attendees = (artifact.metadata or {}).get("attendees")
        if attendees:
            for name in attendees.split(","):
                name = name.strip()
                if name:
                    mentions.append(
                        Mention.create(
                            artifact_id=artifact.id,
                            source=artifact.source,
                            raw_text=name,
                            type="person",
                            content=content,
                            span_start=0,
                            span_end=min(len(name), len(content)),
                            source_identity=name,
                            confidence=0.90,
                        )
                    )
        for match in FIREflies_SPEAKER_RE.finditer(content):
            name = match.group(2).strip()
            mentions.append(
                Mention.create(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    raw_text=name,
                    type="person",
                    content=content,
                    span_start=match.start(2),
                    span_end=match.end(2),
                    confidence=0.88,
                )
            )
        mentions.extend(self._extract_tickets(artifact))
        return mentions

    def _extract_hubspot(self, artifact: Artifact) -> list[Mention]:
        mentions = self._extract_generic(artifact)
        title = artifact.title or ""
        if title and title not in {"QuantaLedger", "random"}:
            mentions.append(
                Mention.create(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    raw_text=title,
                    type="org",
                    content=artifact.content,
                    span_start=0,
                    span_end=min(len(title), len(artifact.content)),
                    confidence=0.82,
                )
            )
        return mentions

    def _extract_confluence(self, artifact: Artifact) -> list[Mention]:
        return self._extract_generic(artifact)

    def _extract_generic(self, artifact: Artifact) -> list[Mention]:
        mentions: list[Mention] = []
        mentions.extend(self._extract_tickets(artifact))
        mentions.extend(self._extract_emails_in_body(artifact))
        mentions.extend(self._extract_usernames(artifact))
        return mentions

    def _extract_tickets(self, artifact: Artifact) -> list[Mention]:
        mentions: list[Mention] = []
        for match in TICKET_RE.finditer(artifact.content):
            ticket = match.group(1)
            mentions.append(
                Mention.create(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    raw_text=ticket,
                    type="ticket",
                    content=artifact.content,
                    span_start=match.start(),
                    span_end=match.end(),
                    source_identity=ticket,
                    confidence=0.95,
                )
            )
        return mentions

    def _extract_emails_in_body(self, artifact: Artifact) -> list[Mention]:
        mentions: list[Mention] = []
        for match in EMAIL_RE.finditer(artifact.content):
            email = match.group(0)
            mentions.append(
                Mention.create(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    raw_text=email,
                    type="email",
                    content=artifact.content,
                    span_start=match.start(),
                    span_end=match.end(),
                    source_identity=email,
                    confidence=0.96,
                )
            )
        return mentions

    def _extract_usernames(self, artifact: Artifact) -> list[Mention]:
        mentions: list[Mention] = []
        for match in USERNAME_RE.finditer(artifact.content):
            handle = f"@{match.group(1)}"
            mentions.append(
                Mention.create(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    raw_text=handle,
                    type="username",
                    content=artifact.content,
                    span_start=match.start(),
                    span_end=match.end(),
                    source_identity=handle,
                    confidence=0.90,
                )
            )
        return mentions


def extract_claims_from_artifact(
    artifact: Artifact,
    *,
    extraction_method: str = "deterministic",
) -> list[Claim]:
    """Extract candidate claims from artifact text using pattern rules."""
    claims: list[Claim] = []
    content = artifact.content
    observed_at = artifact.timestamp

    def add_claim(
        subject: str,
        predicate: str,
        obj: str,
        match: re.Match[str],
        confidence: float,
        valid_from: str | None = None,
        valid_to: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        subject = subject.strip()
        obj = obj.strip()
        if not _valid_entity(subject) or not _valid_entity(obj) or confidence < MIN_CLAIM_CONFIDENCE:
            return
        evidence = content[match.start() : match.end()].strip()
        claims.append(
            Claim.create(
                artifact_id=artifact.id,
                subject_mention=subject,
                predicate=predicate,
                object_mention=obj,
                observed_at=observed_at,
                evidence_span=evidence,
                valid_from=valid_from,
                valid_to=valid_to,
                confidence=confidence,
                extraction_method=extraction_method,
                metadata=metadata or {},
            )
        )

    for match in OWNS_RE.finditer(content):
        add_claim(match.group(1), "OWNS", match.group(2), match, 0.88)

    for match in TAKING_OVER_RE.finditer(content):
        add_claim(match.group(1), "OWNS", match.group(2), match, 0.85)

    for match in ASSIGNED_TO_TICKET_RE.finditer(content):
        add_claim(match.group(1), "ASSIGNED_TO", match.group(2), match, 0.86)

    for match in ASSIGNED_TO_RE.finditer(content):
        obj = artifact.title or "unknown target"
        add_claim(match.group(1), "ASSIGNED_TO", obj, match, 0.80)

    for match in LEADS_RE.finditer(content):
        add_claim(match.group(1), "LEADS", match.group(2), match, 0.82)

    for match in BLOCKS_RE.finditer(content):
        ticket = match.group(1)
        add_claim(artifact.title or "this item", "BLOCKS", ticket, match, 0.84)

    for match in DEPENDS_ON_RE.finditer(content):
        add_claim(artifact.title or "this item", "DEPENDS_ON", match.group(1), match, 0.81)

    for match in REVIEWS_RE.finditer(content):
        add_claim(match.group(1), "REVIEWS", match.group(2), match, 0.83)

    return _dedupe_claims(claims)


def _dedupe_mentions(mentions: list[Mention]) -> list[Mention]:
    seen: set[tuple[str, str, str, int]] = set()
    out: list[Mention] = []
    for mention in mentions:
        key = (mention.artifact_id, mention.raw_text, mention.type, mention.span_start)
        if key in seen:
            continue
        seen.add(key)
        out.append(mention)
    return out


def _dedupe_claims(claims: list[Claim]) -> list[Claim]:
    seen: set[str] = set()
    out: list[Claim] = []
    for claim in claims:
        if claim.claim_id in seen:
            continue
        seen.add(claim.claim_id)
        out.append(claim)
    return out
