"""Feature vector generation for identity-pair gold dataset."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from continuum.entities import candidate_from_mention, compute_features

from .schema import FEATURE_SLOTS, IdentityPairRow, MentionSide

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY = ROOT / "data" / "extraction" / "mention_inventory.json"
DEFAULT_ARTIFACTS = ROOT / "data" / "samples" / "phase2a-sample.jsonl"

PROJECT_KEY_RE = re.compile(r"\b(SUP|ENG|INC|INV|CS|OPS)-\d+\b", re.IGNORECASE)
GITHUB_REPO_RE = re.compile(r"github\.com/[^\s/]+/[^\s/\)]+", re.IGNORECASE)
GITHUB_SLUG_REPO_RE = re.compile(r"(?:^|/)([a-z0-9_.-]+/[a-z0-9_.-]+)(?:/|$)", re.IGNORECASE)


@dataclass
class ArtifactContext:
    projects: set[str] = field(default_factory=set)
    repositories: set[str] = field(default_factory=set)
    channels: set[str] = field(default_factory=set)


@dataclass
class ArtifactIndex:
    by_id: dict[str, dict[str, Any]]
    mention_artifacts: dict[str, set[str]]

    def contexts_for(self, mention: str) -> ArtifactContext:
        artifact_ids = self.mention_artifacts.get(mention, set())
        context = ArtifactContext()
        for artifact_id in artifact_ids:
            artifact = self.by_id.get(artifact_id)
            if artifact is None:
                continue
            context.projects.update(_extract_projects(artifact))
            context.repositories.update(_extract_repositories(artifact))
            context.channels.update(_extract_channels(artifact))
        return context


def load_artifact_index(
    inventory_path: Path = DEFAULT_INVENTORY,
    artifacts_path: Path = DEFAULT_ARTIFACTS,
) -> ArtifactIndex:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    mention_artifacts: dict[str, set[str]] = {}
    for entry in inventory["entries"]:
        mention = entry["raw_mention"]
        mention_artifacts.setdefault(mention, set()).update(entry.get("artifact_ids") or [])

    by_id: dict[str, dict[str, Any]] = {}
    with artifacts_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            artifact = json.loads(line)
            by_id[artifact["id"]] = artifact

    return ArtifactIndex(by_id=by_id, mention_artifacts=mention_artifacts)


def _extract_projects(artifact: dict[str, Any]) -> set[str]:
    text = _artifact_text(artifact)
    return {match.group(0).upper() for match in PROJECT_KEY_RE.finditer(text)}


def _extract_repositories(artifact: dict[str, Any]) -> set[str]:
    repos: set[str] = set()
    text = _artifact_text(artifact)
    for match in GITHUB_REPO_RE.finditer(text):
        repos.add(match.group(0).lower().split("github.com/", 1)[-1].rstrip(").,"))
    metadata = artifact.get("metadata") or {}
    slug = str(metadata.get("slug") or "")
    if artifact.get("source") == "github" and slug.startswith("pr-"):
        repos.add(slug.lower())
    content = str(artifact.get("content") or "")
    if content.startswith("sources/github/"):
        parts = content.split("/")
        if len(parts) >= 3:
            repos.add("/".join(parts[1:3]).lower())
    return repos


def _extract_channels(artifact: dict[str, Any]) -> set[str]:
    if artifact.get("source") != "slack":
        return set()
    title = str(artifact.get("title") or "").strip().lower()
    if title and not title.endswith(".json"):
        return {title}
    content = str(artifact.get("content") or "")
    if content.startswith("sources/slack/"):
        parts = content.split("/")
        if len(parts) >= 3:
            return {parts[2].lower()}
    return set()


def _artifact_text(artifact: dict[str, Any]) -> str:
    metadata = artifact.get("metadata") or {}
    return "\n".join(
        [
            str(artifact.get("title") or ""),
            str(artifact.get("content") or ""),
            str(metadata.get("slug") or ""),
        ]
    )


def _jaccard(a: set[str], b: set[str]) -> float | None:
    if not a and not b:
        return None
    union = a | b
    if not union:
        return None
    return len(a & b) / len(union)


def _overlap_score(a: set[str], b: set[str]) -> float | None:
    if not a or not b:
        return None
    return 1.0 if a & b else 0.0


def _candidate(side: MentionSide):
    source = side.sources[0] if len(side.sources) == 1 else None
    return candidate_from_mention(
        side.mention,
        type=side.type,
        emails=side.emails,
        usernames=side.usernames,
        external_ids=side.external_ids,
        source=source,
        frequency=side.frequency,
    )


def compute_context_features(
    a: MentionSide,
    b: MentionSide,
    index: ArtifactIndex,
) -> dict[str, float | None]:
    a_ids = index.mention_artifacts.get(a.mention, set())
    b_ids = index.mention_artifacts.get(b.mention, set())
    cooccurrence = _jaccard(a_ids, b_ids)

    a_ctx = index.contexts_for(a.mention)
    b_ctx = index.contexts_for(b.mention)
    return {
        "cooccurrence": cooccurrence,
        "shared_project": _overlap_score(a_ctx.projects, b_ctx.projects),
        "shared_repository": _overlap_score(a_ctx.repositories, b_ctx.repositories),
        "shared_channel": _overlap_score(a_ctx.channels, b_ctx.channels),
    }


def compute_embedding_similarity(
    a: MentionSide,
    b: MentionSide,
    *,
    provider: Any | None = None,
) -> float | None:
    if provider is None:
        return None
    texts = [a.mention.strip(), b.mention.strip()]
    if not texts[0] or not texts[1]:
        return None
    vectors = provider.embed(texts)
    if len(vectors) != 2:
        return None
    dot = sum(x * y for x, y in zip(vectors[0], vectors[1]))
    return max(min(dot, 1.0), -1.0)


def build_feature_dict(
    row: IdentityPairRow | dict[str, Any],
    *,
    index: ArtifactIndex,
    embedding_provider: Any | None = None,
) -> dict[str, float | None]:
    pair = row if isinstance(row, IdentityPairRow) else IdentityPairRow.from_dict(row)
    extra = compute_context_features(pair.a, pair.b, index)
    if embedding_provider is not None:
        extra["embedding_similarity"] = compute_embedding_similarity(
            pair.a,
            pair.b,
            provider=embedding_provider,
        )
    else:
        extra["embedding_similarity"] = None

    base = compute_features(_candidate(pair.a), _candidate(pair.b), extra=extra)
    features = base.to_dict()
    for slot in FEATURE_SLOTS:
        features.setdefault(slot, None)
    return {slot: _normalize_feature(features.get(slot)) for slot in FEATURE_SLOTS}


def _normalize_feature(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return None
        return float(value)
    return None


def attach_features(
    rows: list[IdentityPairRow | dict[str, Any]],
    *,
    index: ArtifactIndex | None = None,
    embedding_provider: Any | None = None,
) -> list[dict[str, Any]]:
    artifact_index = index or load_artifact_index()
    enriched: list[dict[str, Any]] = []
    for row in rows:
        pair = row if isinstance(row, IdentityPairRow) else IdentityPairRow.from_dict(row)
        pair.features = build_feature_dict(
            pair,
            index=artifact_index,
            embedding_provider=embedding_provider,
        )
        enriched.append(pair.to_dict())
    return enriched
