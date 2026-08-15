"""Deterministic claim extraction tests."""

from continuum.dataset.artifact import Artifact
from continuum.extract.deterministic import extract_claims_from_artifact


def _artifact(content: str, **kwargs) -> Artifact:
    return Artifact(
        id="dsid_test123456789012345678901234567890",
        source=kwargs.get("source", "slack"),
        source_id="test123456789012345678901234567890",
        type="slack_message",
        author=None,
        timestamp="2026-07-29T00:00:00",
        title=kwargs.get("title", "handoff"),
        content=content,
        metadata={},
    )


def test_owns_pattern():
    artifact = _artifact("Sarah Chen owns the Acme integration.")
    claims = extract_claims_from_artifact(artifact)
    assert any(c.predicate == "OWNS" and c.subject_mention == "Sarah Chen" for c in claims)


def test_taking_over_pattern():
    artifact = _artifact("Sarah Chen is taking over Acme from Arjun Mehta.")
    claims = extract_claims_from_artifact(artifact)
    assert any(c.predicate == "OWNS" and "Acme" in c.object_mention for c in claims)


def test_blocks_pattern():
    artifact = _artifact("This change blocks ENG-5842 until resolved.", title="runtime cleanup")
    claims = extract_claims_from_artifact(artifact)
    assert any(c.predicate == "BLOCKS" and c.object_mention == "ENG-5842" for c in claims)


def test_low_confidence_claims_filtered_by_threshold():
    artifact = _artifact("Maybe someone leads something someday.")
    claims = extract_claims_from_artifact(artifact)
    assert claims == []
