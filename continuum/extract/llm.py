"""Optional LLM-assisted extraction (gap-fill only; off by default)."""

from __future__ import annotations

import time

from continuum.dataset.artifact import Artifact

from .deterministic import DeterministicMentionExtractor, extract_claims_from_artifact
from .llm_client import create_llm_client, llm_available, llm_model_name, parse_json_array
from .schemas import Claim, Mention

try:
    from continuum.eval.experiment import record_llm_call
except ImportError:
    def record_llm_call(_duration_ms: float) -> None:
        return None


class HybridMentionExtractor:
    """Deterministic first; optional LLM gap-fill when Fireworks/OpenAI key is set."""

    def __init__(self, *, use_llm: bool = False) -> None:
        self._deterministic = DeterministicMentionExtractor()
        self._use_llm = use_llm and llm_available()

    def extract(self, artifact: Artifact) -> list[Mention]:
        mentions = self._deterministic.extract(artifact)
        if not self._use_llm or mentions:
            return mentions
        return _llm_mentions(artifact)


class HybridClaimExtractor:
    def __init__(self, *, use_llm: bool = False, merge_llm: bool = False) -> None:
        self._use_llm = use_llm and llm_available()
        self._merge_llm = merge_llm

    def extract(self, artifact: Artifact) -> list[Claim]:
        claims = extract_claims_from_artifact(artifact, extraction_method="deterministic")
        if not self._use_llm:
            return claims
        if not claims:
            return _llm_claims(artifact)
        if not self._merge_llm:
            return claims
        llm_claims = _llm_claims(artifact)
        seen = {c.claim_id for c in claims}
        for claim in llm_claims:
            if claim.claim_id not in seen:
                claims.append(claim)
        return claims


def _llm_mentions(artifact: Artifact) -> list[Mention]:
    try:
        client = create_llm_client()
    except (ImportError, RuntimeError):
        return []
    prompt = (
        "Extract entity mentions from this enterprise artifact. "
        "Return ONLY a JSON array of objects with keys: raw_text, type, source_identity. "
        "Allowed types: person, project, account, ticket, email, username, org. "
        f"Artifact source={artifact.source}\n\n{artifact.content[:4000]}"
    )
    try:
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=llm_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        record_llm_call((time.perf_counter() - started) * 1000)
        payload = parse_json_array(response.choices[0].message.content or "[]")
    except Exception:
        return []
    mentions: list[Mention] = []
    for item in payload:
        raw = str(item.get("raw_text", "")).strip()
        if not raw:
            continue
        idx = artifact.content.find(raw)
        if idx < 0:
            idx = 0
        mentions.append(
            Mention.create(
                artifact_id=artifact.id,
                source=artifact.source,
                raw_text=raw,
                type=str(item.get("type", "person")),
                content=artifact.content,
                span_start=idx,
                span_end=idx + len(raw),
                source_identity=item.get("source_identity"),
                extraction_method="llm",
                confidence=0.70,
            )
        )
    return mentions


def _llm_claims(artifact: Artifact) -> list[Claim]:
    try:
        client = create_llm_client()
    except (ImportError, RuntimeError):
        return []
    prompt = (
        "Extract factual claims as a JSON array with keys: "
        "subject_mention, predicate, object_mention, evidence_span. "
        "Return ONLY JSON. Predicates: OWNS, LEADS, ASSIGNED_TO, BLOCKS, DEPENDS_ON, REVIEWS. "
        "Use verbatim evidence quotes from the text. "
        f"Artifact source={artifact.source}\n\n{artifact.content[:4000]}"
    )
    try:
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=llm_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        record_llm_call((time.perf_counter() - started) * 1000)
        payload = parse_json_array(response.choices[0].message.content or "[]")
    except Exception:
        return []
    claims: list[Claim] = []
    for item in payload:
        try:
            claims.append(
                Claim.create(
                    artifact_id=artifact.id,
                    subject_mention=str(item["subject_mention"]),
                    predicate=str(item["predicate"]),
                    object_mention=str(item["object_mention"]),
                    observed_at=artifact.timestamp,
                    evidence_span=str(item.get("evidence_span", ""))[:500],
                    confidence=0.70,
                    extraction_method="llm",
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return claims
