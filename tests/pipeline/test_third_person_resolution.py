"""Batch 1 — third-person entity extraction (no HydraDB).

A plaintext third-person name in a message body ("Morgan owns Acme") must
mint a person entity and produce a loadable claim, without minting garbage
entities from capitalized tokens that are not relation-verb subjects.

Pure extraction + gate (no HydraDB): resolve_entities_from_artifacts →
extract_claim_records → gate_claims_for_load.
"""

from __future__ import annotations

from continuum.dataset.artifact import Artifact
from continuum.pipeline.source_e2e import (
    extract_claim_records,
    gate_claims_for_load,
    resolve_entities_from_artifacts,
)


def _artifact(
    source: str,
    author: str,
    content: str,
    idx: int,
    *,
    participants: list[dict] | None = None,
    timestamp: str = "2026-08-01T00:00:00+00:00",
) -> Artifact:
    return Artifact(
        id=f"dsid_{idx:032x}",
        source=source,
        source_id=f"{source}-{idx}",
        type="gmail_message" if source == "gmail" else "slack_message",
        author=author,
        timestamp=timestamp,
        title="t",
        content=content,
        metadata={"participants": participants or []},
    )


def _resolutions(artifacts: list[Artifact]) -> dict[str, dict]:
    resolutions, _ = resolve_entities_from_artifacts(artifacts)
    return resolutions


def _loadable(artifacts: list[Artifact], resolutions: dict[str, dict]) -> list[dict]:
    claims, _ = extract_claim_records(artifacts, resolutions, refinement_provider="mock")
    loadable, _rejected = gate_claims_for_load(claims, resolutions, artifacts)
    return loadable


def _person_keys(resolutions: dict[str, dict]) -> set[str]:
    return {k for k in resolutions if k.startswith("person:")}


def _account_keys(resolutions: dict[str, dict]) -> set[str]:
    return {k for k in resolutions if k.startswith("account:")}


def test_third_person_ownership_mints_person_and_claim():
    a = _artifact("slack", "soham", "Morgan owns Acme per the Q4 plan.", 1)
    resolutions = _resolutions([a])
    assert "person:morgan" in _person_keys(resolutions)
    assert "account:acme" in _account_keys(resolutions)
    loadable = _loadable([a], resolutions)
    assert any(c["subject_mention"] == "Morgan" and c["predicate"] == "OWNS" and c["object_mention"] == "Acme" for c in loadable)


def test_third_person_took_over_is_loadable():
    a = _artifact("slack", "soham", "Priya took over Acme.", 2)
    resolutions = _resolutions([a])
    assert "person:priya" in _person_keys(resolutions)
    loadable = _loadable([a], resolutions)
    assert any(c["subject_mention"] == "Priya" and c["object_mention"] == "Acme" for c in loadable)


def test_responsibility_verb_mints_person_and_account():
    a = _artifact("slack", "soham", "Sarah is now responsible for the Redwood account.", 3)
    resolutions = _resolutions([a])
    assert "person:sarah" in _person_keys(resolutions)
    assert "account:redwood" in _account_keys(resolutions)
    loadable = _loadable([a], resolutions)
    assert any(c["subject_mention"] == "Sarah" and c["object_mention"] == "Redwood" for c in loadable)


def test_handed_to_mints_both_persons():
    a = _artifact("slack", "soham", "John handed the project to Maya.", 4)
    resolutions = _resolutions([a])
    persons = _person_keys(resolutions)
    assert "person:john" in persons
    assert "person:maya" in persons


def test_body_name_converges_with_author_handle():
    a = _artifact("slack", "morgan", "Morgan owns Acme.", 5)
    resolutions = _resolutions([a])
    # body "Morgan" and author "morgan" share one slug key
    assert "person:morgan" in _person_keys(resolutions)
    assert "person:morgan" not in {k for k in resolutions if k.endswith("-1")}


def test_novel_name_only_in_body_is_minted_and_loadable():
    a = _artifact("slack", "soham", "Xavier owns Beta Corp.", 6)
    resolutions = _resolutions([a])
    assert "person:xavier" in _person_keys(resolutions)
    assert "account:beta-corp" in _account_keys(resolutions)
    loadable = _loadable([a], resolutions)
    assert any(c["subject_mention"] == "Xavier" for c in loadable)


def test_ambiguous_same_name_prefers_single_entity():
    a = _artifact("slack", "soham", "Morgan owns Acme.", 7)
    b = _artifact("slack", "soham", "Morgan owns Beta.", 8)
    resolutions = _resolutions([a, b])
    # deterministic: one person:morgan entity (slug convergence), not two
    assert resolutions.keys().isdisjoint({"person:morgan-1", "person:morgan-2"})
    assert "person:morgan" in _person_keys(resolutions)


def test_cross_signal_same_person_one_entity_many_aliases():
    slack = _artifact(
        "slack", "Priya Nair", "Priya Nair owns Acme.",
        9,
        participants=[{"user_id": "U9", "display_name": "Priya Nair", "username": "priya.nair"}],
    )
    gmail = _artifact(
        "gmail", "Priya Nair <priya.nair@company.com>", "priya.nair@company.com owns Acme.",
        10,
        participants=[{"email": "priya.nair@company.com", "display_name": "Priya Nair <priya.nair@company.com>"}],
    )
    resolutions = _resolutions([slack, gmail])
    priya = resolutions.get("person:priya-nair") or {}
    aliases = {m.lower() for m in priya.get("mentions", [])}
    assert "priya nair" in aliases
    assert "priya.nair@company.com" in aliases
    assert len(aliases) >= 3


def test_negative_no_relation_verb_not_minted():
    a = _artifact("slack", "soham", "Great work everyone, thanks Morgan!", 11)
    resolutions = _resolutions([a])
    assert "person:morgan" not in _person_keys(resolutions)


def test_negative_non_person_object_not_minted():
    a = _artifact("slack", "soham", "Acme Health dashboard is down.", 12)
    resolutions = _resolutions([a])
    assert "person:acme-health" not in _person_keys(resolutions)
