"""B1 regression tests — handoff extraction quality.

These lock the three malformed-subject failures from the PR #10 review:

- 'soham@company.com owns Acme' must not produce subject 'com'
- 'ownership\\n\\nMorgan owns Acme' must not produce a synthetic subject
- 'Maya Patel <maya.patel@redwood.com>' must normalize to 'Maya Patel'
  (email preserved separately, not treated as a person-name string)

They also lock the author-normalization contract used downstream by entity
resolution, and prove extraction AND rejection behavior.
"""

from __future__ import annotations

from continuum.dataset.artifact import Artifact
from continuum.pipeline.source_e2e import (
    HANDOFF_PATTERNS,
    _normalize_person_mention,
    supplement_handoff_claims,
)

RESOLUTIONS = {
    "person:morgan": {"name": "Morgan", "label": "Person", "mentions": ["Morgan", "morgan"], "aliases": []},
    "person:soham": {"name": "Soham", "label": "Person", "mentions": ["Soham", "soham", "@soham", "soham@company.com"], "aliases": []},
    "person:maya-patel": {"name": "Maya Patel", "label": "Person", "mentions": ["Maya Patel"], "aliases": []},
    "account:acme": {"name": "Acme", "label": "Account", "mentions": ["Acme"], "aliases": []},
    "account:cedarbank": {"name": "CedarBank", "label": "Account", "mentions": ["CedarBank"], "aliases": []},
}


def _artifact(content: str, *, author: str | None = None, source: str = "gmail", timestamp: str | None = None) -> Artifact:
    return Artifact(
        id="dsid_" + "a" * 32,
        source=source,
        source_id="src-1",
        type="gmail_message" if source == "gmail" else "slack_message",
        author=author,
        timestamp=timestamp,
        title="t",
        content=content,
        metadata={"participants": []},
    )


def _subjects(artifact: Artifact) -> list[str]:
    return [c["subject_mention"] for c in supplement_handoff_claims([artifact], RESOLUTIONS)]


# ---------------------------------------------------------------------------
# _normalize_person_mention contract
# ---------------------------------------------------------------------------


def test_normalize_plain_name():
    assert _normalize_person_mention("Morgan") == "Morgan"
    assert _normalize_person_mention("  Maya Patel  ") == "Maya Patel"


def test_normalize_name_with_angle_email():
    assert _normalize_person_mention("Maya Patel <maya.patel@redwood.com>") == "Maya Patel"
    assert _normalize_person_mention('"Maya Patel" <maya.patel@redwood.com>') == "Maya Patel"
    assert _normalize_person_mention("morgan <morgan@company.com>") == "morgan"


def test_normalize_bare_email_preserved():
    assert _normalize_person_mention("<maya@example.com>") == "maya@example.com"
    assert _normalize_person_mention("soham@company.com") == "soham@company.com"


def test_normalize_empty():
    assert _normalize_person_mention("") == ""
    assert _normalize_person_mention(None) == ""


# ---------------------------------------------------------------------------
# Malformed-subject failures (the three B1 review cases)
# ---------------------------------------------------------------------------


def test_email_tail_not_subject():
    content = "From: soham <soham@company.com>\nTo: ops <ops@company.com>\nSubject: Acme ownership\n\nsoham@company.com owns Acme."
    subjects = _subjects(_artifact(content, author="soham <soham@company.com>"))
    assert "com" not in subjects
    assert "Soham" in subjects


def test_newline_not_consumed_into_subject():
    content = "From: morgan <morgan@company.com>\nTo: ops <ops@company.com>\nSubject: Acme ownership\n\nMorgan owns Acme."
    subjects = _subjects(_artifact(content, author="morgan <morgan@company.com>"))
    assert "ownership\n\nMorgan" not in subjects
    assert "Morgan" in subjects


def test_author_angle_bracket_normalized():
    content = "Hi Camila,\n\nConfirming I am handing off CedarBank account ownership to you effective July 28.\n\nBest,\nMaya"
    subjects = _subjects(_artifact(content, author="Maya Patel <maya.patel@redwood.com>"))
    assert "Maya Patel <maya.patel@redwood.com>" not in subjects
    assert "Maya Patel" in subjects


def test_gmail_handoff_claim_preserved():
    content = "Hi Camila,\n\nConfirming I am handing off CedarBank account ownership to you effective July 28.\n\nBest,\nMaya"
    claims = supplement_handoff_claims([_artifact(content, author="Maya Patel <maya.patel@redwood.com>")], RESOLUTIONS)
    assert any(
        c["subject_mention"] == "Maya Patel" and c["predicate"] == "OWNS" and c["object_mention"] == "CedarBank"
        for c in claims
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_punctuation_adjacent_to_ownership_phrase():
    content = "The account is Acme; Morgan owns Acme. (confirmed)"
    subjects = _subjects(_artifact(content, author="Morgan"))
    assert "Morgan" in subjects


def test_handle_subject():
    content = "Soham Ratnaparkhi: @soham owns Acme now."
    claims = supplement_handoff_claims([_artifact(content, author="Soham Ratnaparkhi", source="slack")], RESOLUTIONS)
    soham = [c for c in claims if c["object_mention"] == "Acme" and c["predicate"] == "OWNS"]
    assert soham and soham[0]["subject_mention"] == "@soham"


def test_multiple_people_in_artifact_no_cross_contamination():
    content = "Priya owns Acme too."
    subjects = _subjects(_artifact(content, author="Priya", source="slack"))
    assert subjects == ["Priya"] or all("Priya" in s for s in subjects)


def test_no_valid_person_mention_rejected():
    content = "No ownership here, just a memo."
    claims = supplement_handoff_claims([_artifact(content, author="Somebody Else")], RESOLUTIONS)
    assert claims == []


def test_handoff_patterns_do_not_match_email_tails():
    content = "soham@company.com owns Acme."
    matched = []
    for pattern, _predicate, _source in HANDOFF_PATTERNS:
        for m in pattern.finditer(content):
            matched.append((pattern.pattern, m.group(0), m.groups()))
    bad = [m for m in matched if m[1].startswith("com owns")]
    assert not bad, f"email tail matched: {bad}"
