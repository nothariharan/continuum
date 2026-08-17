"""Deterministic question decomposition — the query-front boundary.

Turns a natural-language question into a QueryContext (intent, entities,
relationships, temporal constraints) with no model and no external API.

This is the layer that makes Continuum source-agnostic: a Slack question,
a Gmail question, and a GitHub question all become the same QueryContext
shape before any retrieval or graph work happens.

Decomposition rules are intentionally conservative:
- entity mentions are extracted by explicit signal (quotes, emails,
  usernames, capitalized name pairs) and left unresolved
- temporal constraints are lifted from explicit/relative time language
- unknown intents fall back to GENERIC rather than guessing
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .context import QueryContext, QueryEntity, QueryRelationship, TemporalConstraint

_MENTION_QUOTED = re.compile(r"'([^']+)'")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_USERNAME_RE = re.compile(r"@[A-Za-z0-9_.-]+")
_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b")
_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTH_YEAR_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b",
    re.IGNORECASE,
)
_QUARTER_RE = re.compile(r"\b[Qq][1-4]\s+(\d{4})\b")

_SKIP_WORDS = frozenset(
    {
        "who", "what", "when", "where", "which", "how", "why", "the", "a", "an",
        "and", "or", "of", "for", "to", "in", "on", "at", "as", "is", "are",
        "was", "were", "be", "been", "with", "by", "from", "that", "this",
        "these", "those", "across", "two", "did", "does", "do", "have", "has",
        "its", "their", "his", "her", "same", "then", "now", "currently",
        "previously", "before", "after", "during", "since", "compare",
        "versus", "vs", "until", "between", "over", "under", "about", "into",
        "within",
    }
)

_INTENT_RULES: list[tuple[str, re.Pattern]] = [
    ("ENTITY_RESOLUTION", re.compile(r"\b(same person|same as|also known as|same account|identical to|is .* and .* the same)\b", re.IGNORECASE)),
    ("PROVENANCE", re.compile(r"\b(which source|which artifact|where does .* come|evidence chain|provenance|which document|which message)\b", re.IGNORECASE)),
    ("CONFLICT", re.compile(r"\b(who actually|which claim|contradicts?|conflicting claims|inconsistent claims|disagree)\b", re.IGNORECASE)),
    ("DECISION", re.compile(r"\b(decided|decision|decided to|decided by|who approved|who chose|who picked)\b", re.IGNORECASE)),
    ("HISTORY", re.compile(r"\b(used to|previously|before|was .* previously|what changed|who owned it then|at that time|originally)\b", re.IGNORECASE)),
    ("DEPENDENCY", re.compile(r"\b(depends on|depend on|blocked by|blocks|relies on|dependency)\b", re.IGNORECASE)),
    ("CO_OCCURRENCE", re.compile(r"\b(who else|who appears|who is also|who else is)\b", re.IGNORECASE)),
    ("LEADERSHIP", re.compile(r"\b(leads?|dri|responsible for|who runs|points of contact|poc)\b", re.IGNORECASE)),
    ("ASSIGNMENT", re.compile(r"\b(assigned to|assignee|who is working on|who handles|who works on|in charge of)\b", re.IGNORECASE)),
    ("OWNERSHIP", re.compile(r"\b(owns|owned|ownership|owner of|does .* belong to|who has .* account)\b", re.IGNORECASE)),
]

_RELATION_HINTS: list[tuple[str, re.Pattern]] = [
    ("OWNS", re.compile(r"\b(owns?|ownership|owned)\b", re.IGNORECASE)),
    ("MAINTAINS", re.compile(r"\b(maintains?|maintenance)\b", re.IGNORECASE)),
    ("LEADS", re.compile(r"\b(leads?|dri)\b", re.IGNORECASE)),
    ("ASSIGNED_TO", re.compile(r"\b(assigned to|assignee|working on|works on)\b", re.IGNORECASE)),
    ("REVIEWS", re.compile(r"\b(reviews?|reviewer)\b", re.IGNORECASE)),
    ("BLOCKS", re.compile(r"\b(blocks?|blocked by)\b", re.IGNORECASE)),
    ("DEPENDS_ON", re.compile(r"\b(depends on|depend on|relies on)\b", re.IGNORECASE)),
]

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def classify_intent(question: str) -> str:
    """Classify the question intent. Conservative: first matching rule wins."""
    lowered = question.lower()
    for intent, pattern in _INTENT_RULES:
        if pattern.search(lowered):
            return intent
    return "GENERIC"


def extract_entities(question: str) -> list[QueryEntity]:
    """Extract unresolved entity mentions (subject/object/other roles).

    Priority: quoted strings, then emails/usernames, then capitalized name
    pairs. Mentions are deliberately unresolved — canonical keys come from
    the entity bridge later.
    """
    entities: list[QueryEntity] = []
    seen: set[str] = set()

    def add(mention: str, role: str, etype: str) -> None:
        m = mention.strip()
        if m and m.lower() not in seen:
            seen.add(m.lower())
            entities.append(QueryEntity(mention=m, role=role, type=etype))

    quoted = _MENTION_QUOTED.findall(question)
    if len(quoted) >= 2:
        add(quoted[0], "subject", "other")
        add(quoted[1], "object", "other")
    else:
        emails = _EMAIL_RE.findall(question)
        if len(emails) >= 2:
            add(emails[0], "subject", "email")
            add(emails[1], "object", "email")
        else:
            usernames = _USERNAME_RE.findall(question)
            if len(usernames) >= 2:
                add(usernames[0], "subject", "username")
                add(usernames[1], "object", "username")
            else:
                names = []
                for match in _NAME_RE.findall(question):
                    words = match.split()
                    if words and words[0].lower() in _SKIP_WORDS:
                        words = words[1:]
                    if not words or " ".join(words).lower() in _SKIP_WORDS:
                        continue
                    names.append(" ".join(words))
                if len(names) >= 2:
                    add(names[0], "subject", "person")
                    add(names[1], "object", "person")
                elif len(names) == 1:
                    add(names[0], "other", "person")
    return entities


def extract_relationships(question: str) -> list[QueryRelationship]:
    """Detect predicate hints. Only graph predicates are returned."""
    lowered = question.lower()
    hints: list[QueryRelationship] = []
    for predicate, pattern in _RELATION_HINTS:
        if pattern.search(lowered):
            hints.append(QueryRelationship(predicate=predicate, raw_hint=predicate))
    return hints


def _iso(value: str) -> str:
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        return value[:10]


def _parse_explicit_date(question: str) -> str | None:
    m = _DATE_RE.search(question)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _QUARTER_RE.search(question)
    if m:
        year = m.group(1)
        q = m.group(0)[1]
        month = {"1": "01", "2": "04", "3": "07", "4": "10"}[q]
        return f"{year}-{month}-01"
    m = _MONTH_YEAR_RE.search(question)
    if m:
        return f"{m.group(2)}-{_MONTHS[m.group(1).lower()]:02d}-01"
    return None


def parse_temporal_constraints(question: str) -> list[TemporalConstraint]:
    """Lift time constraints from the question text.

    Deterministic and conservative: explicit dates win; relative anchors
    (before/after an event) are preserved as anchors for the evidence layer
    to resolve; bare tense signals become current/historical constraints.
    """
    lowered = question.lower()
    constraints: list[TemporalConstraint] = []
    explicit = _parse_explicit_date(question)

    if explicit:
        for phrase in ("as of", "as at", "on"):
            if phrase in lowered:
                constraints.append(
                    TemporalConstraint(kind="as_of", value=explicit, anchor=None, raw=phrase)
                )
                break
        if not any(c.kind == "as_of" for c in constraints):
            constraints.append(
                TemporalConstraint(kind="interval", value=explicit, anchor=None, raw="explicit date")
            )
        if "before" in lowered:
            constraints.append(
                TemporalConstraint(kind="before", value=explicit, anchor=None, raw="before <date>")
            )
        if "after" in lowered:
            constraints.append(
                TemporalConstraint(kind="after", value=explicit, anchor=None, raw="after <date>")
            )
        return constraints

    m = re.search(r"\bbefore\b\s+(?:the\s+|that\s+)?([a-z][a-z0-9 _'-]{1,40}?)(?:[.,]|$|\?|,? (?:who|what|did))", lowered)
    if m and not re.search(r"\b(before \d)", lowered):
        anchor = m.group(1).strip().strip("'")
        constraints.append(
            TemporalConstraint(kind="before", value=None, anchor=anchor or None, raw=m.group(0).strip())
        )

    m = re.search(r"\bafter\b\s+(?:the\s+|that\s+)?([a-z][a-z0-9 _'-]{1,40}?)(?:[.,]|$|\?|,? (?:who|what|did))", lowered)
    if m and not re.search(r"\b(after \d)", lowered):
        anchor = m.group(1).strip().strip("'")
        constraints.append(
            TemporalConstraint(kind="after", value=None, anchor=anchor or None, raw=m.group(0).strip())
        )

    if not constraints:
        past = re.search(r"\b(used to|previously|was .* before|did .* own|originally)\b", lowered)
        if past:
            constraints.append(TemporalConstraint(kind="historical", value=None, anchor=None, raw=past.group(0)))
        present = re.search(r"\b(now|currently|current|today|as of now)\b", lowered)
        if present:
            constraints.append(TemporalConstraint(kind="current", value=None, anchor=None, raw=present.group(0)))

    return constraints


def decompose_question(question: dict[str, Any]) -> QueryContext:
    """Decompose a question dict into a QueryContext (deterministic)."""
    qid = str(question.get("question_id", ""))
    text = str(question.get("question", ""))
    return QueryContext(
        question_id=qid,
        question=text,
        intent=classify_intent(text),
        entities=extract_entities(text),
        relationships=extract_relationships(text),
        temporal=parse_temporal_constraints(text),
    )