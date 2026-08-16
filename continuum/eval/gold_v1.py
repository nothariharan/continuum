"""Continuum Gold Benchmark v1 — loaders, selection, and validation."""

from __future__ import annotations

import json
import random
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from continuum.claims.schema import SUPPORTED_PREDICATES
from continuum.extract.schemas import MENTION_TYPES, read_jsonl, write_jsonl

GOLD_VERSION = "v1"
GOLD_STATUSES = frozenset({"VALID", "AMBIGUOUS", "NO_CLAIM"})

DIFFICULTY_TAGS = (
    "ownership",
    "assignment",
    "leadership",
    "maintenance",
    "dependencies",
    "conflicts",
    "temporal",
    "multi_entity",
    "no_relationship",
    "ambiguous",
    "long_artifact",
    "short_artifact",
    "messy_thread",
)

DEFAULT_SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_LEGACY_LABELS = Path(__file__).resolve().parents[2] / "data" / "labels" / "phase2b-ground-truth.jsonl"
DEFAULT_GOLD_ROOT = Path(__file__).resolve().parents[2] / "data" / "ground_truth" / "v1"


@dataclass(frozen=True)
class GoldClaimRow:
    artifact_id: str
    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    evidence_span: str
    observed_at: str | None
    valid_from: str | None
    valid_to: str | None
    status: str
    notes: str = ""
    difficulty_tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "subject": self.subject,
            "subject_type": self.subject_type,
            "predicate": self.predicate,
            "object": self.object,
            "object_type": self.object_type,
            "evidence_span": self.evidence_span,
            "observed_at": self.observed_at,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "status": self.status,
            "notes": self.notes,
            "difficulty_tags": list(self.difficulty_tags),
        }


@dataclass(frozen=True)
class GoldMentionRow:
    artifact_id: str
    raw_text: str
    type: str
    source_identity: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "raw_text": self.raw_text,
            "type": self.type,
            "source_identity": self.source_identity,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class GoldAmbiguityRow:
    artifact_id: str
    status: str
    notes: str = ""
    difficulty_tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "status": self.status,
            "notes": self.notes,
            "difficulty_tags": list(self.difficulty_tags),
        }


@dataclass
class GoldBenchmark:
    manifest: dict[str, Any]
    artifacts: list[dict[str, Any]]
    mentions: list[GoldMentionRow]
    claims: list[GoldClaimRow]
    ambiguities: list[GoldAmbiguityRow]

    @property
    def artifact_ids(self) -> set[str]:
        return {row["id"] for row in self.artifacts}

    def claims_by_artifact(self) -> dict[str, list[GoldClaimRow]]:
        grouped: dict[str, list[GoldClaimRow]] = {}
        for row in self.claims:
            if row.status == "VALID":
                grouped.setdefault(row.artifact_id, []).append(row)
        return grouped

    def artifact_claim_expectation(self, artifact_id: str) -> str:
        valid = [c for c in self.claims if c.artifact_id == artifact_id and c.status == "VALID"]
        if valid:
            return "VALID"
        for row in self.ambiguities:
            if row.artifact_id == artifact_id:
                return row.status
        ambiguous = [c for c in self.claims if c.artifact_id == artifact_id and c.status == "AMBIGUOUS"]
        if ambiguous:
            return "AMBIGUOUS"
        return "NO_CLAIM"


def git_commit_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def infer_difficulty_tags(artifact: dict[str, Any], mentions: list[dict], claims: list[dict]) -> list[str]:
    tags: list[str] = []
    content = artifact.get("content") or ""
    title = artifact.get("title") or ""
    text = f"{title}\n{content}".lower()

    if len(content) > 8000:
        tags.append("long_artifact")
    elif len(content) < 400:
        tags.append("short_artifact")

    if artifact.get("source") == "slack" and content.count("\n") > 20:
        tags.append("messy_thread")

    predicate_hits = {
        "ownership": bool(re.search(r"\b(owns|owner|ownership|account exec)\b", text)),
        "assignment": bool(re.search(r"\b(assigned|assignee|assigned to)\b", text)),
        "leadership": bool(re.search(r"\b(leads|leadership|director|head of)\b", text)),
        "maintenance": bool(re.search(r"\b(maintains|maintenance|on-call|sre)\b", text)),
        "dependencies": bool(re.search(r"\b(depends on|blocked by|blocks)\b", text)),
        "conflicts": bool(re.search(r"\b(conflict|contradict|disagree)\b", text)),
        "temporal": bool(re.search(r"\b(effective|until|as of|starting|by q[1-4])\b", text)),
    }
    tags.extend(k for k, hit in predicate_hits.items() if hit)

    if len(mentions) >= 6:
        tags.append("multi_entity")
    if not claims and not predicate_hits.get("dependencies"):
        tags.append("no_relationship")
    if any(c.get("ambiguous") for c in claims):
        tags.append("ambiguous")

    return sorted(set(tags))


def select_artifacts_stratified(
    rows: list[dict[str, Any]],
    *,
    count: int = 150,
    seed: int = 20260816,
    legacy_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Pick ~count artifacts covering all sources; prefer legacy gold IDs when provided."""
    rng = random.Random(seed)
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)

    if legacy_ids:
        id_map = {row["id"]: row for row in rows}
        selected = [id_map[i] for i in sorted(legacy_ids) if i in id_map]
        if len(selected) >= count:
            return selected[:count]

    per_source = max(1, count // max(len(by_source), 1))
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sorted(by_source):
        pool = by_source[source][:]
        rng.shuffle(pool)
        for row in pool[:per_source]:
            if row["id"] not in seen:
                selected.append(row)
                seen.add(row["id"])
    if len(selected) < count:
        remaining = [r for r in rows if r["id"] not in seen]
        rng.shuffle(remaining)
        for row in remaining:
            selected.append(row)
            seen.add(row["id"])
            if len(selected) >= count:
                break
    return selected[:count]


def legacy_claim_to_gold(row: dict[str, Any], artifact_id: str, tags: list[str]) -> GoldClaimRow:
    status = "AMBIGUOUS" if row.get("ambiguous") else "VALID"
    return GoldClaimRow(
        artifact_id=artifact_id,
        subject=row["subject_mention"],
        subject_type=_guess_type(row["subject_mention"]),
        predicate=row["predicate"],
        object=row["object_mention"],
        object_type=_guess_type(row["object_mention"], predicate=row["predicate"]),
        evidence_span=row.get("evidence_span") or "",
        observed_at=row.get("observed_at"),
        valid_from=row.get("valid_from"),
        valid_to=row.get("valid_to"),
        status=status,
        notes="bootstrapped from phase2b-ground-truth",
        difficulty_tags=tuple(tags),
    )


def _guess_type(text: str, *, predicate: str | None = None) -> str:
    value = text.strip()
    if re.match(r"^[A-Z]{2,}-\d+", value):
        return "ticket"
    if "@" in value:
        return "email"
    if predicate in {"OWNS", "MAINTAINS"} and len(value.split()) <= 4:
        return "account"
    if predicate in {"LEADS", "ASSIGNED_TO"} and len(value.split()) <= 3:
        return "person"
    if len(value.split()) <= 3 and value[0:1].isupper():
        return "person"
    return "org"


def build_gold_benchmark(
    *,
    sample_path: Path = DEFAULT_SAMPLE,
    legacy_labels_path: Path = DEFAULT_LEGACY_LABELS,
    count: int = 150,
    seed: int = 20260816,
) -> GoldBenchmark:
    sample_rows = list(read_jsonl(sample_path))
    legacy_by_id: dict[str, dict[str, Any]] = {}
    if legacy_labels_path.exists():
        for row in read_jsonl(legacy_labels_path):
            legacy_by_id[row["artifact_id"]] = row

    legacy_ids = set(legacy_by_id) if legacy_by_id else None
    selected = select_artifacts_stratified(sample_rows, count=count, seed=seed, legacy_ids=legacy_ids)

    mentions: list[GoldMentionRow] = []
    claims: list[GoldClaimRow] = []
    ambiguities: list[GoldAmbiguityRow] = []

    for artifact in selected:
        legacy = legacy_by_id.get(artifact["id"], {})
        legacy_mentions = legacy.get("mentions", [])
        legacy_claims = legacy.get("claims", [])
        tags = infer_difficulty_tags(artifact, legacy_mentions, legacy_claims)

        for mention in legacy_mentions:
            mentions.append(
                GoldMentionRow(
                    artifact_id=artifact["id"],
                    raw_text=mention["raw_text"],
                    type=mention["type"],
                    source_identity=mention.get("source_identity"),
                    notes=legacy.get("notes", ""),
                )
            )

        valid_bootstrapped = False
        for claim in legacy_claims:
            gold_claim = legacy_claim_to_gold(claim, artifact["id"], tags)
            claims.append(gold_claim)
            if gold_claim.status == "VALID":
                valid_bootstrapped = True

        if not valid_bootstrapped and not legacy_claims:
            ambiguities.append(
                GoldAmbiguityRow(
                    artifact_id=artifact["id"],
                    status="NO_CLAIM",
                    notes="no validated claim label yet — abstention expected",
                    difficulty_tags=tuple(tags or ["no_relationship"]),
                )
            )

    source_counts = Counter(row["source"] for row in selected)
    manifest = {
        "version": GOLD_VERSION,
        "dataset_version": f"gold-{GOLD_VERSION}-{seed}",
        "artifact_count": len(selected),
        "mention_count": len(mentions),
        "claim_count": len(claims),
        "ambiguity_count": len(ambiguities),
        "selection_seed": seed,
        "source_coverage": dict(sorted(source_counts.items())),
        "commit_sha": git_commit_sha(),
        "difficulty_tag_vocab": list(DIFFICULTY_TAGS),
        "notes": "Bootstrap from phase2b-ground-truth; claim labels expand incrementally.",
    }

    return GoldBenchmark(
        manifest=manifest,
        artifacts=selected,
        mentions=mentions,
        claims=claims,
        ambiguities=ambiguities,
    )


def write_gold_benchmark(benchmark: GoldBenchmark, root: Path = DEFAULT_GOLD_ROOT) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": root / "manifest.json",
        "artifacts": root / "artifacts.jsonl",
        "mentions": root / "mentions.jsonl",
        "claims": root / "claims.jsonl",
        "ambiguities": root / "ambiguities.jsonl",
    }
    paths["manifest"].write_text(json.dumps(benchmark.manifest, indent=2) + "\n", encoding="utf-8")
    write_jsonl(paths["artifacts"], benchmark.artifacts)
    write_jsonl(paths["mentions"], [m.to_dict() for m in benchmark.mentions])
    write_jsonl(paths["claims"], [c.to_dict() for c in benchmark.claims])
    write_jsonl(paths["ambiguities"], [a.to_dict() for a in benchmark.ambiguities])
    return paths


def load_gold_benchmark(root: Path = DEFAULT_GOLD_ROOT) -> GoldBenchmark:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    artifacts = list(read_jsonl(root / "artifacts.jsonl"))
    mentions = [
        GoldMentionRow(
            artifact_id=row["artifact_id"],
            raw_text=row["raw_text"],
            type=row["type"],
            source_identity=row.get("source_identity"),
            notes=row.get("notes", ""),
        )
        for row in read_jsonl(root / "mentions.jsonl")
    ]
    claims = [
        GoldClaimRow(
            artifact_id=row["artifact_id"],
            subject=row["subject"],
            subject_type=row["subject_type"],
            predicate=row["predicate"],
            object=row["object"],
            object_type=row["object_type"],
            evidence_span=row.get("evidence_span", ""),
            observed_at=row.get("observed_at"),
            valid_from=row.get("valid_from"),
            valid_to=row.get("valid_to"),
            status=row["status"],
            notes=row.get("notes", ""),
            difficulty_tags=tuple(row.get("difficulty_tags") or []),
        )
        for row in read_jsonl(root / "claims.jsonl")
    ]
    ambiguities = [
        GoldAmbiguityRow(
            artifact_id=row["artifact_id"],
            status=row["status"],
            notes=row.get("notes", ""),
            difficulty_tags=tuple(row.get("difficulty_tags") or []),
        )
        for row in read_jsonl(root / "ambiguities.jsonl")
    ]
    return GoldBenchmark(
        manifest=manifest,
        artifacts=artifacts,
        mentions=mentions,
        claims=claims,
        ambiguities=ambiguities,
    )


def validate_gold_benchmark(benchmark: GoldBenchmark) -> list[str]:
    errors: list[str] = []
    if benchmark.manifest.get("version") != GOLD_VERSION:
        errors.append("manifest.version must be v1")

    artifact_ids = benchmark.artifact_ids
    if len(artifact_ids) != len(benchmark.artifacts):
        errors.append("duplicate artifact ids in artifacts.jsonl")

    for mention in benchmark.mentions:
        if mention.artifact_id not in artifact_ids:
            errors.append(f"mention references unknown artifact {mention.artifact_id}")
        if mention.type not in MENTION_TYPES:
            errors.append(f"invalid mention type {mention.type!r}")

    for claim in benchmark.claims:
        if claim.artifact_id not in artifact_ids:
            errors.append(f"claim references unknown artifact {claim.artifact_id}")
        if claim.status not in GOLD_STATUSES:
            errors.append(f"invalid claim status {claim.status!r}")
        if claim.predicate not in SUPPORTED_PREDICATES:
            errors.append(f"unsupported predicate {claim.predicate!r}")

    for row in benchmark.ambiguities:
        if row.artifact_id not in artifact_ids:
            errors.append(f"ambiguity references unknown artifact {row.artifact_id}")
        if row.status not in {"NO_CLAIM", "AMBIGUOUS"}:
            errors.append(f"ambiguity status must be NO_CLAIM or AMBIGUOUS, got {row.status!r}")

    expected_sources = {
        "slack",
        "gmail",
        "linear",
        "github",
        "jira",
        "confluence",
        "google_drive",
        "hubspot",
        "fireflies",
    }
    covered = set(benchmark.manifest.get("source_coverage", {}))
    missing = expected_sources - covered
    if missing:
        errors.append(f"missing source coverage: {sorted(missing)}")

    return errors
