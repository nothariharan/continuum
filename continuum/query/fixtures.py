"""Synthetic cross-source fixtures for the core-query path.

A deterministic multi-source scenario (Slack, Gmail, GitHub, Jira, Fireflies)
that exercises the query core without any external API or dataset download:

  - a clean ownership succession   (Priya -> Morgan, disjoint intervals)
  - a contradictory ownership pair (overlapping intervals -> conflict)
  - an unorderable ownership pair  (no timestamps -> review)
  - maintenance + assignment claims (other predicates)
  - a decision event artifact for DECISION-intent decomposition

Every artifact carries source provenance (source_id, source_url, thread_id)
so the provenance chain can be traced back to the original source message.
Claims use the shared contract (continuum.claims.schema.Claim) and validate
against the loader's entity-pair rules.

This module is pure (no HydraDB). The integration test loads these fixtures
through hydradb.claims.load_claims.
"""

from __future__ import annotations

from continuum.claims.schema import Claim


def build_cross_source_scenario() -> dict:
    sources = [
        {"key": "source:slack", "name": "Slack"},
        {"key": "source:gmail", "name": "Gmail"},
        {"key": "source:github", "name": "GitHub"},
        {"key": "source:jira", "name": "Jira"},
        {"key": "source:fireflies", "name": "Fireflies"},
    ]

    artifacts = [
        {
            "key": "artifact:acme-handoff",
            "kind": "slack_message",
            "content": "Morgan is now owning Acme. Handing over the account keys today.",
            "title": "Acme ownership handoff",
            "source_id": "source:slack",
            "observed_at": "2026-06-10",
            "source_url": "slack://C123/msg/172000",
            "thread_id": "C123:t1",
        },
        {
            "key": "artifact:acme-ownership-email",
            "kind": "gmail_message",
            "content": "Confirming Priya owns Acme effective May 1. We will transition ownership on June 10.",
            "title": "Acme ownership confirmation",
            "source_id": "source:gmail",
            "observed_at": "2026-05-01",
            "source_url": "gmail://thread/aa11",
            "thread_id": "aa11",
        },
        {
            "key": "artifact:acme-repo",
            "kind": "github_pr",
            "content": "Morgan maintains the acme repo. PR #42 merged.",
            "title": "Acme repo maintenance",
            "source_id": "source:github",
            "observed_at": "2026-06-11",
            "source_url": "github://acme/pr/42",
            "thread_id": "pr:42",
        },
        {
            "key": "artifact:acme-onboarding",
            "kind": "jira_ticket",
            "content": "Acme onboarding assigned to Priya. Owner Morgan. Blocked by acme-repo merge.",
            "title": "Acme onboarding ticket",
            "source_id": "source:jira",
            "observed_at": "2026-06-12",
            "source_url": "jira://ACME-101",
            "thread_id": "ACME-101",
        },
        {
            "key": "artifact:acme-renewal-decision",
            "kind": "meeting_transcript",
            "content": "Priya decided to delay the Acme renewal until Q3. Sarah recorded the decision.",
            "title": "Acme renewal decision review",
            "source_id": "source:fireflies",
            "observed_at": "2026-06-13",
            "source_url": "fireflies://meeting/88",
            "thread_id": "meeting:88",
        },
        {
            "key": "artifact:acme-conflict-note",
            "kind": "slack_message",
            "content": "Hold on, Priya still owns Acme as of today. Morgan was only reviewing.",
            "title": "Acme ownership correction",
            "source_id": "source:slack",
            "observed_at": "2026-06-12",
            "source_url": "slack://C123/msg/172500",
            "thread_id": "C123:t1",
        },
    ]

    claims = [
        Claim.create(
            artifact_id="artifact:acme-ownership-email",
            subject_mention="Priya",
            predicate="OWNS",
            object_mention="Acme",
            observed_at="2026-05-01",
            valid_from="2026-05-01",
            valid_to="2026-06-09",
            evidence_span="Priya owns Acme effective May 1",
        ),
        Claim.create(
            artifact_id="artifact:acme-handoff",
            subject_mention="Morgan",
            predicate="OWNS",
            object_mention="Acme",
            observed_at="2026-06-10",
            valid_from="2026-06-10",
            valid_to=None,
            evidence_span="Morgan is now owning Acme",
        ),
        Claim.create(
            artifact_id="artifact:acme-conflict-note",
            subject_mention="Priya",
            predicate="OWNS",
            object_mention="Acme",
            observed_at="2026-06-10",
            valid_from="2026-06-10",
            valid_to=None,
            evidence_span="Priya still owns Acme as of today",
        ),
        Claim.create(
            artifact_id="artifact:acme-repo",
            subject_mention="Morgan",
            predicate="MAINTAINS",
            object_mention="acme-repo",
            observed_at="2026-06-11",
            valid_from="2026-06-11",
            valid_to=None,
            evidence_span="Morgan maintains the acme repo",
        ),
        Claim.create(
            artifact_id="artifact:acme-onboarding",
            subject_mention="Priya",
            predicate="ASSIGNED_TO",
            object_mention="Acme",
            observed_at="2026-06-12",
            valid_from="2026-06-12",
            valid_to=None,
            evidence_span="Acme onboarding assigned to Priya",
        ),
    ]

    resolutions = {
        "person:priya": {
            "label": "Person",
            "name": "Priya",
            "mentions": ["Priya", "priya@acme.com", "@priya"],
            "aliases": ["priya@acme.com", "@priya"],
        },
        "person:morgan": {
            "label": "Person",
            "name": "Morgan",
            "mentions": ["Morgan", "@morgan"],
            "aliases": ["@morgan"],
        },
        "person:sarah": {
            "label": "Person",
            "name": "Sarah",
            "mentions": ["Sarah"],
            "aliases": [],
        },
        "account:acme": {
            "label": "Account",
            "name": "Acme",
            "mentions": ["Acme"],
            "aliases": ["acme"],
        },
        "project:acme-repo": {
            "label": "Project",
            "name": "acme-repo",
            "mentions": ["acme repo", "acme-repo"],
            "aliases": ["acme-repo"],
        },
    }

    questions = [
        {
            "question_id": "q_cross_current",
            "question": "Who currently owns Acme?",
        },
        {
            "question_id": "q_cross_before",
            "question": "Who owned Acme before the handoff?",
        },
        {
            "question_id": "q_cross_asof",
            "question": "As of 2026-06-05, who owned Acme?",
        },
        {
            "question_id": "q_cross_conflict",
            "question": "Who actually owns Acme right now?",
        },
        {
            "question_id": "q_cross_maintain",
            "question": "Who maintains acme-repo?",
        },
        {
            "question_id": "q_cross_decision",
            "question": "Who decided to delay the Acme renewal?",
        },
    ]

    return {
        "sources": sources,
        "artifacts": artifacts,
        "claims": claims,
        "resolutions": resolutions,
        "questions": questions,
    }