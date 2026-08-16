"""Relation extraction unit tests — deterministic patterns, candidate-gated.

Each test builds a tiny lexicon + artifact and asserts exact claim output.
No graph, no network, no LLM. The safety property under test: relations can
connect candidates, never invent entities.
"""

from __future__ import annotations

from continuum.dataset.artifact import Artifact
from continuum.extract.v2.candidates import find_candidates
from continuum.extract.v2.relations import extract_relations

LEXICON = {
    "person:sarah": {
        "name": "Sarah Chen",
        "label": "Person",
        "mentions": ["Sarah Chen", "Sarah"],
        "aliases": ["sarah_csm"],
    },
    "person:priyom": {
        "name": "Priyom Das",
        "label": "Person",
        "mentions": ["Priyom Das", "Priyom"],
        "aliases": [],
    },
    "account:acme": {
        "name": "ACME",
        "label": "Account",
        "mentions": ["ACME"],
        "aliases": ["acme"],
    },
    "account:acme-health": {
        "name": "Acme Health",
        "label": "Account",
        "mentions": ["Acme Health", "Acme Health Inc."],
        "aliases": ["acmehealth.com"],
    },
    "account:lucentgrid": {
        "name": "LucentGrid",
        "label": "Account",
        "mentions": ["LucentGrid"],
        "aliases": ["lucentgrid"],
    },
}


def _artifact(content: str, source: str = "fireflies", title: str = "LucentGrid POC") -> Artifact:
    return Artifact(
        id="dsid_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        source=source,
        source_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        type=f"{source}_message",
        author=None,
        timestamp="2026-07-29T00:00:00",
        title=title,
        content=content,
        metadata={},
    )


def _claims(artifact: Artifact) -> list[dict]:
    candidates = find_candidates(artifact, LEXICON)
    return extract_relations(artifact, candidates, LEXICON)


def test_owner_line_ae_owns():
    artifact = _artifact(
        "Owner: Sarah Chen - Send security summary\nOwner: Priyom Das - Draft benchmark\n"
        "Attendees: Sarah (Redwood AE), Priyom (Redwood SE)"
    )
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Sarah Chen", "OWNS", "LucentGrid") in by_pair
    assert ("Priyom Das", "ASSIGNED_TO", "LucentGrid") in by_pair


def test_owner_line_se_assigned():
    artifact = _artifact(
        "Owner: Priyom Das - Draft benchmark plan\nAttendees: Priyom (Redwood SE)"
    )
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Priyom Das", "ASSIGNED_TO", "LucentGrid") in by_pair
    assert ("Priyom Das", "OWNS", "LucentGrid") not in by_pair


def test_attendee_role_ae_leads():
    artifact = _artifact("Attendees: Sarah (Redwood AE), Rina (CSM)")
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Sarah Chen", "LEADS", "LucentGrid") in by_pair


def test_attendee_role_se_maintains():
    artifact = _artifact("Attendees: Priyom (Redwood SE)")
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Priyom Das", "MAINTAINS", "LucentGrid") in by_pair


def test_owner_line_beats_attendee_role():
    artifact = _artifact(
        "Owner: Sarah Chen - Send pack\nAttendees: Sarah (Redwood AE)"
    )
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Sarah Chen", "OWNS", "LucentGrid") in by_pair
    assert ("Sarah Chen", "LEADS", "LucentGrid") not in by_pair


def test_email_thread_domain_ownership():
    artifact = _artifact(
        "From: Acme Customer <amy@acmehealth.com>\n"
        "To: Sarah Chen <sarah.chen@redwood.com>\n"
        "Subject: renewal\n\nHi Sarah,",
        source="gmail",
        title="Acme renewal",
    )
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Sarah Chen", "OWNS", "Acme Health") in by_pair


def test_email_ae_label_owns_account():
    artifact = _artifact(
        "From: Acme Customer <amy@acmehealth.com>\n"
        "To: Priyom Das <priyom.das@redwood.com>\n"
        "Subject: MSA\n\nLooping in Priyom (AE) to weigh in.",
        source="gmail",
        title="Acme MSA",
    )
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Priyom Das", "OWNS", "Acme Health") in by_pair


def test_passive_assigned_to_person():
    artifact = _artifact("Action items assigned to Sarah Chen: provide config JSON.")
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Sarah Chen", "ASSIGNED_TO", "LucentGrid") in by_pair


def test_verb_owns_pattern():
    artifact = _artifact("Sarah Chen owns Acme Health.")
    claims = _claims(artifact)
    by_pair = {(c["subject_mention"], c["predicate"], c["object_mention"]) for c in claims}
    assert ("Sarah Chen", "OWNS", "Acme Health") in by_pair


def test_claims_are_graph_shaped():
    artifact = _artifact("Owner: Sarah Chen - Send summary")
    claims = _claims(artifact)
    assert claims
    for claim in claims:
        for key in ("claim_id", "artifact_id", "subject_mention", "predicate",
                    "object_mention", "observed_at", "valid_from", "valid_to",
                    "confidence", "extraction_method", "evidence_span"):
            assert key in claim
        assert claim["observed_at"] == "2026-07-29T00:00:00"
        assert claim["evidence_span"].strip()
        assert claim["extraction_method"] == "deterministic-v2"


def test_no_candidates_no_claims():
    artifact = _artifact("The model latency looks fine today.")
    assert _claims(artifact) == []


def test_evidence_span_is_verbatim():
    artifact = _artifact("Owner: Sarah Chen - Send security summary")
    claims = _claims(artifact)
    assert claims[0]["evidence_span"] == "Owner: Sarah Chen -"
    assert claims[0]["evidence_span"] in artifact.content
