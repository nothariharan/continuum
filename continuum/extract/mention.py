"""Mention extraction orchestration."""

from __future__ import annotations

from typing import Protocol

from continuum.dataset.artifact import Artifact

from .deterministic import DeterministicMentionExtractor
from .schemas import Mention, mention_to_dict


class MentionExtractor(Protocol):
    def extract(self, artifact: Artifact) -> list[Mention]: ...


def extract_mentions(
    artifacts: list[Artifact],
    *,
    method: str = "deterministic",
) -> list[Mention]:
    if method == "deterministic":
        extractor: MentionExtractor = DeterministicMentionExtractor()
    elif method in {"llm", "hybrid"}:
        from .llm import HybridMentionExtractor

        extractor = HybridMentionExtractor(use_llm=True)
    else:
        raise ValueError(f"unknown mention extraction method: {method}")
    mentions: list[Mention] = []
    for artifact in artifacts:
        mentions.extend(extractor.extract(artifact))
    return mentions


def mentions_to_jsonl_rows(mentions: list[Mention]) -> list[dict]:
    return [mention_to_dict(m) for m in mentions]
