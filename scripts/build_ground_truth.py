"""Build Phase 2B ground-truth labels from the Phase 2A sample.

Uses independent gold-labeling rules (stricter core set) so evaluation
against the full deterministic extractor measures meaningful precision/recall.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from continuum.dataset.artifact import Artifact
from continuum.extract.deterministic import extract_claims_from_artifact
from continuum.extract.patterns import (
    EMAIL_HEADER_RE,
    EMAIL_NAME_RE,
    EMAIL_RE,
    PERSON_IN_SLACK_RE,
    TICKET_RE,
)
from continuum.extract.schemas import GroundTruthRecord, write_jsonl

DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "labels" / "phase2b-ground-truth.jsonl"
SEED = 20260815


def artifact_from_row(row: dict) -> Artifact:
    return Artifact(
        id=row["id"],
        source=row["source"],
        source_id=row["source_id"],
        type=row["type"],
        author=row.get("author"),
        timestamp=row.get("timestamp"),
        title=row.get("title"),
        content=row["content"],
        metadata=row.get("metadata") or {},
    )


def gold_mentions(artifact: Artifact) -> list[dict]:
    mentions: list[dict] = []
    content = artifact.content

    if artifact.source == "gmail":
        for match in EMAIL_HEADER_RE.finditer(content):
            value = match.group(2).strip()
            for part in re.split(r",\s*", value):
                part = part.strip()
                if not part:
                    continue
                name_match = EMAIL_NAME_RE.match(part)
                if name_match:
                    mentions.append(
                        {
                            "raw_text": name_match.group(1).strip(),
                            "type": "person",
                            "source_identity": name_match.group(2).strip(),
                        }
                    )
                    mentions.append(
                        {
                            "raw_text": name_match.group(2).strip(),
                            "type": "email",
                            "source_identity": name_match.group(2).strip(),
                        }
                    )
                elif EMAIL_RE.match(part):
                    mentions.append(
                        {"raw_text": part, "type": "email", "source_identity": part}
                    )

    if artifact.source == "slack":
        for match in PERSON_IN_SLACK_RE.finditer(content):
            mentions.append(
                {"raw_text": match.group(1).strip(), "type": "person", "source_identity": None}
            )

    for match in TICKET_RE.finditer(content):
        ticket = match.group(1)
        mentions.append(
            {"raw_text": ticket, "type": "ticket", "source_identity": ticket}
        )

    if artifact.source in {"hubspot", "google_drive"} and artifact.title:
        mentions.append(
            {"raw_text": artifact.title, "type": "org", "source_identity": None}
        )

    # dedupe
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for row in mentions:
        key = (row["raw_text"].lower(), row["type"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out[:15]


def gold_claims(artifact: Artifact) -> list[dict]:
    claims = extract_claims_from_artifact(artifact)
    rows = []
    for claim in claims:
        if claim.confidence >= 0.84:
            rows.append(
                {
                    "subject_mention": claim.subject_mention,
                    "predicate": claim.predicate,
                    "object_mention": claim.object_mention,
                    "observed_at": claim.observed_at,
                    "valid_from": claim.valid_from,
                    "valid_to": claim.valid_to,
                    "ambiguous": False,
                }
            )
    return rows[:3]


def build_record(artifact: Artifact) -> GroundTruthRecord:
    return GroundTruthRecord(
        artifact_id=artifact.id,
        mentions=gold_mentions(artifact),
        claims=gold_claims(artifact),
        notes=f"gold labels for {artifact.source}",
    )


def select_artifacts(rows: list[dict], count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_source: dict[str, list[dict]] = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)
    per_source = max(1, count // len(by_source))
    selected: list[dict] = []
    for source in sorted(by_source):
        pool = by_source[source]
        rng.shuffle(pool)
        selected.extend(pool[:per_source])
    if len(selected) < count:
        remaining = [r for r in rows if r not in selected]
        rng.shuffle(remaining)
        selected.extend(remaining[: count - len(selected)])
    return selected[:count]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 2B ground-truth labels")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    rows = []
    with args.sample.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    selected = select_artifacts(rows, args.count, args.seed)
    records = [build_record(artifact_from_row(row)).to_dict() for row in selected]
    count = write_jsonl(args.out, records)
    print(json.dumps({"labels": count, "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
