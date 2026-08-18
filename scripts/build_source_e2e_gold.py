#!/usr/bin/env python3
"""Build the cross-source E2E gold fixture package."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from continuum.dataset.artifact import artifact_to_dict
from continuum.pipeline.source_e2e import ingest_from_manifest, repo_commit_sha

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "ground_truth" / "source-e2e-v1"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_manifest(commit_sha: str) -> dict:
    return {
        "version": "source-e2e-v1",
        "commit_sha": commit_sha,
        "fireworks_budget_cap": 20,
        "ingested_at": "2026-01-01T00:00:00+00:00",
        "fixture_files": {
            "slack": [
                "cross_reference_handoff.json",
                "mentions_and_links.json",
                "soham_handoff.json",
                "acme_conflict.json",
                "acme_handoff_slack.json",
            ],
            "gmail": [
                "handoff_thread.json",
                "soham_ownership.json",
                "acme_handoff_morgan.json",
            ],
        },
        "programmatic_artifacts": [],
    }


def gold_resolutions() -> dict:
    return {
        "person:maya-patel": {
            "label": "Person",
            "name": "Maya Patel",
            "mentions": ["Maya Patel", "Maya", "maya.patel", "maya.patel@redwood.com"],
            "aliases": [],
        },
        "person:camila-reyes": {
            "label": "Person",
            "name": "Camila Reyes",
            "mentions": ["Camila Reyes", "Camila", "camila.reyes", "camila.reyes@redwood.com"],
            "aliases": [],
        },
        "person:soham-ratnaparkhi": {
            "label": "Person",
            "name": "Soham Ratnaparkhi",
            "mentions": ["Soham Ratnaparkhi", "Soham", "soham", "@soham", "soham@company.com"],
            "aliases": [],
        },
        "person:morgan": {
            "label": "Person",
            "name": "Morgan",
            "mentions": ["Morgan", "morgan", "morgan@company.com"],
            "aliases": [],
        },
        "person:priya": {
            "label": "Person",
            "name": "Priya",
            "mentions": ["Priya", "priya"],
            "aliases": [],
        },
        "person:zoe-martinez": {
            "label": "Person",
            "name": "Zoe Martinez",
            "mentions": ["Zoe Martinez", "zoe.martinez"],
            "aliases": [],
        },
        "account:cedarbank": {
            "label": "Account",
            "name": "CedarBank",
            "mentions": ["CedarBank"],
            "aliases": [],
        },
        "account:acme": {
            "label": "Account",
            "name": "Acme",
            "mentions": ["Acme"],
            "aliases": [],
        },
        "account:acme-health": {
            "label": "Account",
            "name": "Acme Health",
            "mentions": ["Acme Health"],
            "aliases": [],
        },
    }


def gold_questions() -> list[dict]:
    return [
        {"question_id": "se2e-01", "category": "single-hop", "question": "Who owns CedarBank now?", "expected_answer": "Camila Reyes", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
        {"question_id": "se2e-02", "category": "temporal", "question": "Who owned CedarBank before Camila Reyes?", "expected_answer": "Maya Patel", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
        {"question_id": "se2e-03", "category": "single-hop", "question": "Who owns Acme now?", "expected_answer": "Soham Ratnaparkhi", "evidence_entity": "account:acme", "predicate": "OWNS"},
        {"question_id": "se2e-04", "category": "cross-source", "question": "Who owns Acme now after the handoff?", "expected_answer": "Priya", "evidence_entity": "account:acme", "predicate": "OWNS"},
        {"question_id": "se2e-05", "category": "temporal", "question": "Who owned Acme before Priya?", "expected_answer": "Morgan", "evidence_entity": "account:acme", "predicate": "OWNS"},
        {"question_id": "se2e-06", "category": "conflict", "question": "Who actually owns Acme right now?", "expected_answer": "CONFLICT: Morgan or Priya", "evidence_entity": "account:acme", "predicate": "OWNS"},
        {"question_id": "se2e-07", "category": "provenance", "question": "Show the evidence chain for who owns CedarBank.", "expected_answer": "2 claim(s) via Gmail, Slack", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
        {"question_id": "se2e-08", "category": "multi-hop", "question": "Which source contains evidence that Camila Reyes owns CedarBank?", "expected_answer": "Slack", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
        {"question_id": "se2e-09", "category": "entity-resolution", "question": "Are '@soham' and 'soham@company.com' the same person?", "expected_answer": "same", "evidence_entity": None, "predicate": None},
        {"question_id": "se2e-10", "category": "abstention", "question": "Who owns Acme Health?", "expected_answer": "unknown - abstain", "evidence_entity": "account:acme-health", "predicate": "OWNS"},
        {"question_id": "se2e-11", "category": "temporal", "question": "When did Camila Reyes become owner of CedarBank?", "expected_answer": "2026-07-28", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
        {"question_id": "se2e-12", "category": "provenance", "question": "Which claim and artifact support Soham Ratnaparkhi owning Acme?", "expected_answer": "claim", "evidence_entity": "account:acme", "predicate": "OWNS"},
        {"question_id": "se2e-13", "category": "single-hop", "question": "Who owns Acme according to Gmail?", "expected_answer": "Soham Ratnaparkhi|Morgan", "evidence_entity": "account:acme", "predicate": "OWNS"},
        {"question_id": "se2e-14", "category": "cross-source", "question": "Does Slack or Gmail show the CedarBank handoff?", "expected_answer": "Gmail|Slack", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
        {"question_id": "se2e-15", "category": "conflict", "question": "What are the conflicting ownership claims for Acme?", "expected_answer": "CONFLICT", "evidence_entity": "account:acme", "predicate": "OWNS"},
        {"question_id": "se2e-16", "category": "temporal", "question": "Who owned CedarBank as of 2026-07-27?", "expected_answer": "Maya Patel", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
        {"question_id": "se2e-17", "category": "single-hop", "question": "Who is taking over CedarBank ownership?", "expected_answer": "Camila Reyes", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
        {"question_id": "se2e-18", "category": "entity-resolution", "question": "Is 'Morgan' the same as 'morgan@company.com'?", "expected_answer": "same", "evidence_entity": None, "predicate": None},
        {"question_id": "se2e-19", "category": "abstention", "question": "Who maintains Acme Health?", "expected_answer": "unknown - abstain", "evidence_entity": "account:acme-health", "predicate": "MAINTAINS"},
        {"question_id": "se2e-20", "category": "multi-hop", "question": "What artifacts support CedarBank ownership?", "expected_answer": "gmail artifact", "evidence_entity": "account:cedarbank", "predicate": "OWNS"},
    ]


def gold_claims(artifacts_by_title: dict[str, str]) -> list[dict]:
    """Hand-verified claims keyed by artifact content markers."""
    rows: list[dict] = []

    def add(artifact_id: str, subject: str, predicate: str, obj: str, observed: str, evidence: str, **kwargs):
        from continuum.claims.schema import Claim

        claim = Claim.create(
            artifact_id=artifact_id,
            subject_mention=subject,
            predicate=predicate,
            object_mention=obj,
            observed_at=observed,
            evidence_span=evidence,
            valid_from=kwargs.get("valid_from"),
            valid_to=kwargs.get("valid_to"),
            extraction_method="gold-v1",
        )
        rows.append(claim.to_dict())

    for art_id, content in artifacts_by_title.items():
        if "CedarBank ownership from July 28" in content or "handing off CedarBank" in content:
            if "Camila" in content and "handing off" in content:
                add(art_id, "Maya Patel", "OWNS", "CedarBank", "2026-07-27", "handing off CedarBank", valid_to="2026-07-27")
            elif "taking over CedarBank" in content:
                add(art_id, "Camila Reyes", "OWNS", "CedarBank", "2026-07-28", "taking over CedarBank ownership", valid_from="2026-07-28")
            elif "still own CedarBank" in content:
                add(art_id, "Maya Patel", "OWNS", "CedarBank", "2026-07-20", "still own CedarBank", valid_from="2026-07-01", valid_to="2026-07-27")
        if "@soham owns Acme" in content:
            add(art_id, "Soham", "OWNS", "Acme", "2024-10-08", "@soham owns Acme now")
        if "soham@company.com owns Acme" in content:
            add(art_id, "Soham", "OWNS", "Acme", "2024-10-09", "soham@company.com owns Acme")
        if content.strip().endswith("Morgan owns Acme.") and "Priya" not in content:
            add(art_id, "Morgan", "OWNS", "Acme", "2024-10-01", "Morgan owns Acme", valid_from="2024-10-01", valid_to="2024-10-07")
        if "Priya is taking over Acme" in content:
            add(art_id, "Priya", "OWNS", "Acme", "2024-10-08", "Priya is taking over Acme", valid_from="2024-10-08")
        if "Morgan owns Acme." in content and "Priya owns Acme too" in content:
            pass
        elif content.count("owns Acme") >= 2 or ("Morgan owns Acme" in content and "Priya owns Acme too" in content):
            if "Morgan owns Acme" in content:
                add(art_id, "Morgan", "OWNS", "Acme", "2024-10-05", "Morgan owns Acme", valid_from="2024-10-05", valid_to="2024-10-05")
            if "Priya owns Acme too" in content:
                add(art_id, "Priya", "OWNS", "Acme", "2024-10-05", "Priya owns Acme too", valid_from="2024-10-05", valid_to="2024-10-05")

    return rows


def gold_mentions(resolutions: dict) -> list[dict]:
    rows = []
    for entity_key, definition in resolutions.items():
        for mention in definition.get("mentions", []):
            rows.append(
                {
                    "entity_key": entity_key,
                    "mention": mention,
                    "label": definition.get("label"),
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build source E2E gold fixture")
    parser.add_argument("--out", type=Path, default=GOLD)
    args = parser.parse_args()

    commit_sha = repo_commit_sha()
    manifest = build_manifest(commit_sha)
    manifest["gold_dir"] = str(args.out)
    manifest["rebuild_artifacts"] = True

    artifacts = ingest_from_manifest(manifest)
    artifact_rows = [artifact_to_dict(a) for a in artifacts]
    artifacts_by_content = {a.id: a.content or "" for a in artifacts}

    resolutions = gold_resolutions()
    claims = gold_claims(artifacts_by_content)
    questions = gold_questions()
    mentions = gold_mentions(resolutions)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(args.out / "artifacts.jsonl", artifact_rows)
    _write_jsonl(args.out / "claims.jsonl", claims)
    _write_jsonl(args.out / "questions.jsonl", questions)
    _write_jsonl(args.out / "mentions.jsonl", mentions)
    (args.out / "resolutions.json").write_text(json.dumps(resolutions, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"artifacts": len(artifact_rows), "claims": len(claims), "questions": len(questions), "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
