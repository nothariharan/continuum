"""Detailed failure classification for extracted claims (founder extraction-v2).

Subdivides the two dominant checkpoint failure classes:

- INVALID_SUBJECT / INVALID_OBJECT -> what kind of string is the mention?
    document_title   mention equals the artifact title (title-as-entity)
    sentence_fragment mention is a long multi-word phrase (>= 6 words)
    generic_noun     lowercase common noun with no proper-name shape
    technical_concept capitalized word/abbreviation that is not a lexicon entity
    unknown_person   proper-name-shaped (Title Case words) but not in lexicon
    unknown_other    anything else not in the lexicon

- MISSING_TIMESTAMP -> why is there no observation time?
    artifact_has_ts_but_not_copied   artifact.timestamp set, claim.observed_at null
    source_ts_in_metadata            metadata has a ts_source but no artifact timestamp
    explicit_date_in_text            a real date appears in the content
    relative_date_only               only relative dates (today, next week) in text
    genuinely_no_timestamp           nothing anywhere

Also computes the lexicon-constrained ceiling: how many claims *could* pass if
every mention resolved and every timestamp resolved (predicate/entity-pair gate).

Usage:
    python scripts/classify_claim_failures.py \
        [--claims data/extraction/claims.jsonl] \
        [--resolutions data/fixtures/phase2b/resolutions-checkpoint50.json] \
        [--artifacts data/samples/phase2a-sample.jsonl] \
        [--out data/metadata/claim_failure_classification.json]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from continuum.claims import SUPPORTED_PREDICATES
from continuum.hydradb.claims import ENTITY_PAIR_RULES, pair_supported

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLAIMS = ROOT / "data" / "extraction" / "claims.jsonl"
DEFAULT_RESOLUTIONS = ROOT / "data" / "fixtures" / "phase2b" / "resolutions-checkpoint50.json"
DEFAULT_ARTIFACTS = ROOT / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_OUT = ROOT / "data" / "metadata" / "claim_failure_classification.json"

TITLE_CASE_WORD = re.compile(r"^[A-Z][a-z]")
EXPLICIT_DATE_RE = re.compile(
    r"\b(20[0-9]{2})-?[0-9]{1,2}(?:-?[0-9]{1,2})?\b"
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+[0-9]{1,2},?\s+20[0-9]{2}\b"
    r"|\b20[0-9]{2}[-/][0-9]{1,2}[-/][0-9]{1,2}\b"
)
RELATIVE_DATE_RE = re.compile(
    r"\b(today|tomorrow|yesterday|this week|next week|next monday|monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday|eow|eod|q[1-4]|this quarter|next quarter)\b",
    re.IGNORECASE,
)


def classify_subject(mention: str, artifact: dict, lexicon: set[str]) -> str:
    if mention in lexicon:
        return "lexicon_entity"
    title = (artifact.get("title") or "").strip()
    if mention == title:
        return "document_title"
    words = mention.split()
    if len(words) >= 6:
        return "sentence_fragment"
    if len(words) > 1 and any(ch in mention for ch in ":/|"):
        return "sentence_fragment"
    if mention.islower() or (len(words) == 1 and words[0].islower()):
        return "generic_noun"
    if all(TITLE_CASE_WORD.match(word) for word in words):
        return "unknown_person"
    return "unknown_other"


def classify_missing_timestamp(claim: dict, artifact: dict) -> str:
    if artifact.get("timestamp"):
        return "artifact_has_ts_but_not_copied"
    metadata = artifact.get("metadata") or {}
    if metadata.get("ts_source"):
        return "source_ts_in_metadata"
    content = artifact.get("content") or ""
    if EXPLICIT_DATE_RE.search(content):
        return "explicit_date_in_text"
    if RELATIVE_DATE_RE.search(content):
        return "relative_date_only"
    return "genuinely_no_timestamp"


def main(claims_path: Path, resolutions_path: Path, artifacts_path: Path, out_path: Path) -> dict:
    resolutions = json.loads(resolutions_path.read_text(encoding="utf-8"))
    lexicon = {mention for definition in resolutions.values() for mention in definition.get("mentions", [])}
    lexicon_labels = {mention: definition["label"] for definition in resolutions.values() for mention in definition.get("mentions", [])}

    artifacts = {row["id"]: row for row in (json.loads(line) for line in artifacts_path.open(encoding="utf-8") if line.strip())}

    subject_classes: Counter[str] = Counter()
    object_classes: Counter[str] = Counter()
    timestamp_classes: Counter[str] = Counter()
    predicate_gate: Counter[str] = Counter()
    detail = []
    ceiling = 0
    loadable_predicates: Counter[str] = Counter()

    for line in claims_path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        claim = json.loads(line)
        artifact = artifacts.get(claim.get("artifact_id")) or {}
        subject = str(claim.get("subject_mention", ""))
        object_ = str(claim.get("object_mention", ""))
        predicate = str(claim.get("predicate", ""))

        subj_class = classify_subject(subject, artifact, lexicon)
        obj_class = classify_subject(object_, artifact, lexicon)
        subject_classes[subj_class] += 1
        object_classes[obj_class] += 1

        observed = claim.get("observed_at")
        if not observed:
            timestamp_classes[classify_missing_timestamp(claim, artifact)] += 1
        elif not artifact.get("timestamp"):
            timestamp_classes["claim_has_ts_artifact_does_not"] += 1

        subj_ok = subj_class == "lexicon_entity"
        obj_ok = obj_class == "lexicon_entity"
        pair_ok = False
        if subj_ok and obj_ok:
            slabel = lexicon_labels[subject]
            olabel = lexicon_labels[object_]
            pair_ok = pair_supported(predicate, slabel, olabel)
        predicate_gate["passes_entity_gates" if (subj_ok and obj_ok and pair_ok) else "blocked"] += 1

        could_pass = subj_ok and obj_ok and pair_ok
        if could_pass:
            ceiling += 1
            loadable_predicates[predicate] += 1

        detail.append(
            {
                "claim_id": claim.get("claim_id"),
                "artifact_id": claim.get("artifact_id"),
                "subject_mention": subject[:90],
                "object_mention": object_[:90],
                "predicate": predicate,
                "subject_class": subj_class,
                "object_class": obj_class,
                "timestamp_class": classify_missing_timestamp(claim, artifact) if not observed else "observed_at_present",
                "graph_loadable_if_resolved": could_pass,
            }
        )

    report = {
        "gate": "claim-failure-classification",
        "claims_attempted": len(detail),
        "subjects": dict(subject_classes),
        "objects": dict(object_classes),
        "timestamps": dict(timestamp_classes),
        "entity_gate": dict(predicate_gate),
        "lexicon_ceiling": {
            "count": ceiling,
            "predicates": dict(loadable_predicates),
            "note": "claims that would be graph-loadable if every mention resolved "
            "to the lexicon and every timestamp were provided",
        },
        "detail": detail,
    }
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument("--resolutions", type=Path, default=DEFAULT_RESOLUTIONS)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = main(args.claims, args.resolutions, args.artifacts, args.out)
    for key, value in report.items():
        if key != "detail":
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
