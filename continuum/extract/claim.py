"""Claim extraction orchestration."""

from __future__ import annotations

from typing import Protocol

from continuum.dataset.artifact import Artifact

from .deterministic import extract_claims_from_artifact
from .schemas import Claim, claim_to_dict


class ClaimExtractor(Protocol):
    def extract(self, artifact: Artifact) -> list[Claim]: ...


class DeterministicClaimExtractor:
    def extract(self, artifact: Artifact) -> list[Claim]:
        return extract_claims_from_artifact(artifact, extraction_method="deterministic")


def extract_claims(
    artifacts: list[Artifact],
    *,
    method: str = "deterministic",
) -> list[Claim]:
    if method == "deterministic":
        extractor: ClaimExtractor = DeterministicClaimExtractor()
        claims: list[Claim] = []
        for artifact in artifacts:
            claims.extend(extractor.extract(artifact))
        return claims
    if method in {"llm", "hybrid"}:
        from .llm import HybridClaimExtractor

        extractor = HybridClaimExtractor(use_llm=True, merge_llm=(method == "llm"))
        claims = []
        for artifact in artifacts:
            claims.extend(extractor.extract(artifact))
        return claims
    raise ValueError(f"unknown claim extraction method: {method}")


def claims_to_jsonl_rows(claims: list[Claim]) -> list[dict]:
    return [claim_to_dict(c) for c in claims]
