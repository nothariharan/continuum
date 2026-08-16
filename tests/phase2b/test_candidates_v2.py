"""Candidate detection unit tests — lexicon-gated, deterministic, fast.

Each test builds a tiny inline lexicon and asserts exact candidate output.
No graph, no network, no LLM.
"""

from __future__ import annotations

from continuum.dataset.artifact import Artifact
from continuum.extract.v2.candidates import find_candidates

LEXICON = {
    "person:sarah": {
        "name": "Sarah Chen",
        "label": "Person",
        "mentions": ["Sarah Chen", "Sarah"],
        "aliases": ["sarah_csm"],
    },
    "person:soham": {
        "name": "Soham Ratnaparkhi",
        "label": "Person",
        "mentions": ["Soham Ratnaparkhi", "Soham"],
        "aliases": ["soham", "soham-dev", "S. Ratnaparkhi"],
    },
    "account:acme": {
        "name": "ACME",
        "label": "Account",
        "mentions": ["ACME", "Acme Health"],
        "aliases": ["acme"],
    },
}


def _artifact(content: str, title: str = "handoff") -> Artifact:
    return Artifact(
        id="dsid_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        source="slack",
        source_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        type="slack_message",
        author=None,
        timestamp="2026-07-29T00:00:00",
        title=title,
        content=content,
        metadata={},
    )


def test_person_and_account_detected():
    artifact = _artifact("Sarah is taking over Acme.")
    candidates = find_candidates(artifact, LEXICON)
    by_key = {c.entity_key: c for c in candidates}
    assert set(by_key) == {"person:sarah", "account:acme"}
    assert by_key["person:sarah"].mention == "Sarah"
    assert by_key["person:sarah"].label == "Person"
    assert by_key["account:acme"].mention == "Acme"
    assert by_key["account:acme"].label == "Account"


def test_longest_match_wins():
    artifact = _artifact("Acme Health is renewing. Acme is happy.")
    candidates = find_candidates(artifact, LEXICON)
    acme = [c for c in candidates if c.entity_key == "account:acme"]
    assert len(acme) == 1
    assert acme[0].mention == "Acme Health"


def test_aliases_map_to_same_entity():
    artifact = _artifact("Ping @soham and S. Ratnaparkhi about this.")
    candidates = find_candidates(artifact, LEXICON)
    soham = [c for c in candidates if c.entity_key == "person:soham"]
    assert len(soham) == 1
    assert soham[0].mention in {"soham", "@soham"}


def test_generic_noun_not_a_candidate():
    artifact = _artifact("The model latency looks fine today.")
    candidates = find_candidates(artifact, LEXICON)
    assert candidates == []


def test_no_false_positive_inside_other_words():
    artifact = _artifact("cacmeworkspace is a codename.")
    candidates = find_candidates(artifact, LEXICON)
    assert candidates == []


def test_title_and_body_offsets():
    artifact = _artifact(
        "Priya owns nothing relevant here.",
        title="Sarah takes over Acme",
    )
    candidates = find_candidates(artifact, LEXICON)
    by_mention = {c.mention: c for c in candidates}
    assert "Sarah" in by_mention
    assert "Acme" in by_mention
    sarah = by_mention["Sarah"]
    acme = by_mention["Acme"]
    # Sarah appears in the title before the body separator
    assert sarah.span_start < acme.span_start
    # Context must include the surrounding evidence window
    assert "takes over" in sarah.context
    assert acme.span_start < len(artifact.title) + len(artifact.content)


def test_case_insensitive_match():
    artifact = _artifact("sarah chen is on the thread about ACME.")
    candidates = find_candidates(artifact, LEXICON)
    assert {c.entity_key for c in candidates} == {"person:sarah", "account:acme"}


def test_dedupe_same_entity_via_mention_and_alias():
    artifact = _artifact("Sarah Chen and @sarah_csm are both here.")
    candidates = find_candidates(artifact, LEXICON)
    sarah = [c for c in candidates if c.entity_key == "person:sarah"]
    assert len(sarah) == 1
