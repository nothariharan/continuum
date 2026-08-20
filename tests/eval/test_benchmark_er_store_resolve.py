"""Unit tests for benchmark ER store mention resolution helpers."""

from __future__ import annotations

from continuum.entities.candidates import normalize_slug, signals_from_mention
from continuum.entities.models import CanonicalEntity
from continuum.entities.store import EntityStore


class _FakeClient:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def execute(self, query: str, parameters: dict | None = None):
        class _Result:
            def __init__(self, rows: list[dict]) -> None:
                self.rows = rows

        return _Result(self._rows)


def _project_entity() -> CanonicalEntity:
    return CanonicalEntity(
        entity_key="project:cedar-bank",
        label="Project",
        name="Cedar Bank",
        aliases={"Cedar Bank", "cedar-bank"},
        mentions={"Cedar Bank"},
    )


def test_normalize_slug_collapses_hyphens():
    assert normalize_slug("cedar-bank") == normalize_slug("Cedar Bank")


def test_signals_from_mention_parses_email_and_username():
    email = signals_from_mention("morgan@company.com")
    assert "morgan@company.com" in email.emails
    handle = signals_from_mention("@morgan")
    assert "@morgan" in handle.usernames


def test_resolve_mention_company_suffix():
    entity = CanonicalEntity(
        entity_key="account:acme",
        label="Account",
        name="Acme Corp",
        aliases={"Acme Corp", "Acme"},
        mentions={"Acme Corp"},
    )
    row = {
        "key": entity.entity_key,
        "label": entity.label,
        "name": entity.name,
        "aliases": "|".join(entity.aliases),
        "alias_sources": "{}",
        "emails": "",
        "usernames": "",
        "external_ids": "",
        "sources": "",
        "provenance": "[]",
    }
    store = EntityStore(_FakeClient([row]))  # type: ignore[arg-type]
    payload = store.resolve_mention("Acme Corp")
    assert payload["status"] == "definitive"
    assert payload["entity_key"] == "account:acme"


def test_resolve_mention_slug_match():
    entity = _project_entity()
    row = {
        "key": entity.entity_key,
        "label": entity.label,
        "name": entity.name,
        "aliases": "|".join(entity.aliases),
        "alias_sources": "{}",
        "emails": "",
        "usernames": "",
        "external_ids": "",
        "sources": "",
        "provenance": "[]",
    }
    store = EntityStore(_FakeClient([row]))  # type: ignore[arg-type]
    payload = store.resolve_mention("cedar-bank")
    assert payload["status"] == "definitive"
    assert payload["entity_key"] == "project:cedar-bank"
