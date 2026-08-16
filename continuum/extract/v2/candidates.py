"""Candidate entity detection — lexicon-gated, before relation extraction.

The candidate set is the resolutions lexicon itself (Phase 2B manual scope):
a claim can only enter the graph when both mentions resolve to a lexicon
entity with a canonical predicate pair. Detecting candidates first, then
extracting relations only *between candidates*, prevents the model/patterns
from inventing arbitrary nouns, document titles, or sentence fragments as
entities.

Each candidate carries: mention text (as written in the artifact), the
resolved lexicon key/label, confidence, and the span(s) where it appears.

Performance: one compiled alternation regex per lexicon (cached), so a whole
artifact is scanned in a single pass regardless of lexicon size.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from continuum.dataset.artifact import Artifact

from .envelope import EvidenceEnvelope, build_envelope

WORD_BOUNDARY_PREFIX = r"(?<![\w])"
WORD_BOUNDARY_SUFFIX = r"(?![\w])"


@dataclass(frozen=True)
class Candidate:
    mention: str          # verbatim text found in the artifact
    entity_key: str       # lexicon key, e.g. person:neha-kapoor
    label: str            # Person / Account / Project / Service / Team
    confidence: float
    span_start: int
    span_end: int
    context: str = ""

    @property
    def is_person(self) -> bool:
        return self.label == "Person"


def _build_matcher(resolutions: dict[str, dict[str, Any]]):
    """Compile one alternation regex over all lexicon mentions/aliases.

    Alternatives are ordered longest-first: Python's regex engine tries
    alternatives left-to-right, so at any position the longest mention wins.
    Returns (regex, entries) where entries[i] describes alternative i.
    """
    entries: list[tuple[str, str, str, float]] = []
    for entity_key, definition in resolutions.items():
        label = str(definition.get("label", ""))
        for mention in definition.get("mentions", []):
            entries.append((str(mention), entity_key, label, 0.95))
        for alias in definition.get("aliases", []):
            entries.append((str(alias), entity_key, label, 0.87))
    entries.sort(key=lambda item: len(item[0]), reverse=True)

    pattern = WORD_BOUNDARY_PREFIX + "(?:" + "|".join(
        re.escape(mention) for mention, _, _, _ in entries
    ) + ")" + WORD_BOUNDARY_SUFFIX
    regex = re.compile(pattern, re.IGNORECASE)
    return regex, entries


_matcher_cache: dict[str, Any] = {}


def _get_matcher(resolutions: dict[str, dict[str, Any]]):
    key = id(resolutions)
    cached = _matcher_cache.get(key)
    if cached is not None:
        return cached
    matcher = _build_matcher(resolutions)
    _matcher_cache[key] = matcher
    return matcher


def find_candidates(
    artifact: Artifact,
    resolutions: dict[str, dict[str, Any]],
    envelope: EvidenceEnvelope | None = None,
) -> list[Candidate]:
    """Find all lexicon mention/alias occurrences in the artifact (one pass).

    Longest mention wins at a position; one candidate per resolved entity
    (first occurrence kept).
    """
    envelope = envelope or build_envelope(artifact)
    content = artifact.content or ""
    title = artifact.title or ""
    text = f"{title}\n{content}"

    regex, entries = _get_matcher(resolutions)
    entry_by_lower: dict[str, tuple[str, str, str, float]] = {}
    for entry in entries:
        entry_by_lower.setdefault(entry[0].lower(), entry)

    candidates: list[Candidate] = []
    seen: set[str] = set()
    for match in regex.finditer(text):
        entry = entry_by_lower.get(match.group(0).lower())
        if entry is None:
            continue
        key = entry[1]
        if key in seen:
            continue
        seen.add(key)
        start, end = match.start(), match.end()
        ctx_start = max(0, start - 100)
        ctx_end = min(len(text), end + 100)
        candidates.append(
            Candidate(
                mention=text[start:end].strip(),
                entity_key=key,
                label=entry[2],
                confidence=entry[3],
                span_start=start,
                span_end=end,
                context=text[ctx_start:ctx_end].replace("\n", " ").strip(),
            )
        )
    return candidates
