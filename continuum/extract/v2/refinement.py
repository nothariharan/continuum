"""Predicate refinement provider — resolves the last bit of semantic ambiguity.

The deterministic layer produces subject/object/evidence/candidate-predicate.
The refinement provider may only pick a predicate from a strict enum (or
ABSTAIN). It can never invent entities, evidence, or timestamps.

Provider-agnostic: the extraction pipeline depends only on the
PredicateRefinementProvider protocol. Backends:

- FireworksPredicateProvider  (hosted open-source model, OpenAI-compatible)
- MockPredicateProvider       (deterministic, for tests / dry runs)
- OllamaPredicateProvider     (future local backend)

All providers return a RefinementResult. ABSTAIN means the evidence was
insufficient — the claim must not enter the graph.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Protocol

from continuum.claims import SUPPORTED_PREDICATES

from ..llm_client import create_llm_client, llm_model_name

ABSTAIN = "ABSTAIN"
VALID_PREDICATES = frozenset(SUPPORTED_PREDICATES) | {ABSTAIN}

SYSTEM_PROMPT = """You are a predicate classifier inside an enterprise knowledge graph.

You are NOT allowed to invent entities, evidence, or timestamps.
Choose exactly one predicate from the ALLOWED PREDICATES list. Use only the supplied artifact.

Precise semantics:
- OWNS: the person owns the customer account or is the primary accountable owner of the relationship (AE, CSM, meeting owner).
- MAINTAINS: the person is the technical or operational owner doing the work (SE, engineering, ops, revenue ops).
- LEADS: the person leads an engagement/initiative/review for the account (point of contact coordinating a review).
- ASSIGNED_TO: the person is assigned specific work items.
- BLOCKS / DEPENDS_ON / REVIEWS: use only when the evidence explicitly supports them.

Evidence for ownership is explicit role labels like AE, CSM, "owner", "meeting owner".
Evidence for maintenance is technical/operational role labels like SE, engineer, ops, "technical owner".
Evidence for leading is coordinating a review/initiative as point of contact.

If the artifact does not give a clear role or responsibility signal, return:
{"predicate": "ABSTAIN", "confidence": 0.0}

Return JSON only: {"predicate": "...", "confidence": 0.0-1.0}"""

_HINT = (
    "\n\nHint: the deterministic extractor produced the candidate predicate from email-thread "
    "context. Reconsider it against the precise semantics above. Be conservative: prefer ABSTAIN "
    "over a guess when the artifact lacks an explicit role or responsibility signal."
)


def _build_prompt(context: dict) -> str:
    lines = [
        "SUBJECT:",
        str(context["subject"]),
        "TYPE:",
        str(context["subject_type"]),
        "",
        "OBJECT:",
        str(context["object"]),
        "TYPE:",
        str(context["object_type"]),
        "",
        "CANDIDATE PREDICATE:",
        str(context["candidate_predicate"]),
        "",
        "ALLOWED PREDICATES:",
        " ".join(sorted(context["allowed_predicates"])),
    ]
    context_window = context.get("context_window")
    artifact = context.get("artifact")
    if artifact:
        lines += ["", "ARTIFACT (verbatim):", str(artifact)[:4000]]
    elif context_window:
        lines += ["", "ARTIFACT CONTEXT (verbatim, around the subject):", str(context_window)]
    headers = context.get("headers")
    if headers:
        lines += ["", "EMAIL HEADERS:", str(headers)]
    return "\n".join(lines) + _HINT


def _extract_json(text: str) -> dict | None:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                payload = json.loads(match.group(0))
                return payload if isinstance(payload, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def validate_refinement(payload: dict | None) -> dict:
    """Validate a model payload into {predicate, confidence, valid}.

    Predicate must be in the strict enum; confidence must be a float in
    [0, 1]. Everything else is discarded.
    """
    if not isinstance(payload, dict):
        return {"predicate": ABSTAIN, "confidence": 0.0, "valid": False}
    predicate = str(payload.get("predicate", "")).strip().upper()
    if predicate not in VALID_PREDICATES:
        return {"predicate": ABSTAIN, "confidence": 0.0, "valid": False}
    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    if not (0.0 <= confidence <= 1.0):
        confidence = 0.0
    return {"predicate": predicate, "confidence": confidence, "valid": True}


@dataclass(frozen=True)
class RefinementResult:
    predicate: str
    confidence: float
    reason: str = ""
    latency_ms: float = 0.0
    provider: str = "mock"

    @property
    def abstained(self) -> bool:
        return self.predicate == ABSTAIN


class PredicateRefinementProvider(Protocol):
    def refine(self, context: dict) -> RefinementResult: ...


class MockPredicateProvider:
    """Deterministic provider: returns the candidate predicate unchanged.

    Useful for tests, dry runs, and as the fallback when no API key exists.
    """

    provider_name = "mock"

    def refine(self, context: dict) -> RefinementResult:
        return RefinementResult(
            predicate=str(context.get("candidate_predicate", ABSTAIN)),
            confidence=context.get("candidate_confidence", 0.7),
            reason="mock provider: candidate predicate kept",
            provider=self.provider_name,
        )


class FireworksPredicateProvider:
    """Hosted open-source model refinement via the OpenAI-compatible API.

    Strictly constrained: JSON-only output, enum validation, confidence
    validation, abstention on parse failure.
    """

    provider_name = "fireworks"

    def __init__(self, model: str | None = None, timeout: float = 20.0) -> None:
        self._model = model or llm_model_name()
        self._timeout = timeout

    def refine(self, context: dict) -> RefinementResult:
        from openai import OpenAI

        base_url = os.environ.get("CONTINUUM_LLM_BASE_URL")
        api_key = os.environ.get("FIREWORKS_API_KEY", "").strip()
        if not api_key:
            return RefinementResult(
                predicate=ABSTAIN, confidence=0.0,
                reason="no FIREWORKS_API_KEY configured",
                provider=self.provider_name,
            )
        client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.fireworks.ai/inference/v1",
            timeout=self._timeout,
            max_retries=1,
        )
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_prompt(context)},
                ],
                temperature=0,
                max_tokens=800,
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                # some models occasionally return empty; one retry
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _build_prompt(context)},
                    ],
                    temperature=0,
                    max_tokens=800,
                )
                content = (response.choices[0].message.content or "").strip()
        except Exception as exc:
            latency = (time.perf_counter() - started) * 1000
            return RefinementResult(
                predicate=ABSTAIN, confidence=0.0,
                reason=f"provider error: {exc}", latency_ms=latency,
                provider=self.provider_name,
            )
        latency = (time.perf_counter() - started) * 1000
        payload = validate_refinement(_extract_json(content))
        return RefinementResult(
            predicate=payload["predicate"],
            confidence=payload["confidence"],
            reason=f"model output: {content[:200]}" if payload["valid"] else f"invalid model output: {content[:120]}",
            latency_ms=latency,
            provider=self.provider_name,
        )


def create_refinement_provider(name: str = "auto", model: str | None = None) -> PredicateRefinementProvider:
    """Factory: auto -> Fireworks when key present, else Mock."""
    if name == "mock":
        return MockPredicateProvider()
    if name in {"fireworks", "auto"}:
        from ..llm_client import llm_available

        if name == "auto" and not llm_available():
            return MockPredicateProvider()
        return FireworksPredicateProvider(model=model)
    raise ValueError(f"unknown refinement provider: {name}")
