"""Continuum answer pipeline — layered, inspectable, benchmark-facing.

Question
  → retrieval            (which artifacts/claims are candidates)
  → entity resolution    (mention → canonical key via EntityStore)
  → traversal            (HydraDB hops: claim → artifact → source)
  → state resolution     (current/historical state, conflicts)
  → evidence selection   (evidence chain for the answer)
  → answer generation    (model-agnostic; pluggable generator)

Each layer records its own latency and output into the frozen contract, so
the benchmark can attribute failures ("retrieval failed" vs "state failed").

The answer generator is deliberately model-agnostic: the default generator
is deterministic (uses the state envelope). A model-based generator can be
injected without changing the pipeline.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from continuum.hydradb import HydraDBClient
from continuum.query import (
    resolve_provenance,
    resolve_state,
    resolve_state_on,
)
from continuum.query.conflict import resolve_conflict_state
from continuum.query.context import QueryContext
from continuum.query.decompose import decompose_question
from continuum.query.temporal import resolve_state_for_constraints

from .contract import LAYER_NAMES, empty_result

AnswerGenerator = Callable[[dict[str, Any]], str]

_MENTION_RE = re.compile(r"'([^']+)'|\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_USERNAME_RE = re.compile(r"@[A-Za-z0-9_.-]+")


def _default_as_of() -> str:
    """Fallback 'as of' date when a temporal question has no extracted date."""
    from datetime import date

    return date.today().isoformat()


def _extract_mentions(question_text: str) -> list[str]:
    """Two mentions from a question.

    Priority: quoted strings, then emails/usernames, then name pairs.
    """
    quoted = re.findall(r"'([^']+)'", question_text)
    if len(quoted) >= 2:
        return quoted[:2]
    # emails in the question (possibly inside quotes already consumed)
    emails = _EMAIL_RE.findall(question_text)
    if len(emails) >= 2:
        return emails[:2]
    names = [
        m for m in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", question_text)
        if m.lower() not in {"who", "the", "same", "are", "and", "as", "is", "a", "an", "of", "or", "across", "two"}
    ]
    return names[:2]


def _pair_with_inventory_signals(mentions: list[str], question_text: str) -> IdentityPair:
    """Build an IdentityPair enriched with mention-inventory signals.

    Mirrors the e2e benchmark: emails/usernames/external ids from the real
    mention inventory give the resolver real identity evidence.
    """
    import json

    from continuum.entities.pairs import IdentityPair

    inventory_path = Path(__file__).resolve().parents[2] / "data" / "extraction" / "mention_inventory.json"
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        by_mention = {entry["raw_mention"]: entry for entry in inventory["entries"]}
    except (OSError, json.JSONDecodeError):
        by_mention = {}

    def side(mention: str, index: int) -> dict:
        entry = by_mention.get(mention, {})
        return dict(
            pair_id=f"q:{mentions[0]}:{mentions[1]}:{index}",
            mention=mention,
            type=entry.get("type", "person"),
            source=entry.get("source"),
            emails=tuple(entry.get("emails") or ()),
            usernames=tuple(entry.get("usernames") or ()),
            external_ids=tuple(entry.get("external_ids") or ()),
            label="UNCERTAIN",
        )

    a, b = side(mentions[0], 0), side(mentions[1], 1)
    return IdentityPair(
        pair_id=f"q:{mentions[0]}:{mentions[1]}",
        mention_a=a["mention"], type_a=a["type"], source_a=a["source"],
        emails_a=a["emails"], usernames_a=a["usernames"], external_ids_a=a["external_ids"],
        mention_b=b["mention"], type_b=b["type"], source_b=b["source"],
        emails_b=b["emails"], usernames_b=b["usernames"], external_ids_b=b["external_ids"],
        label="UNCERTAIN",
    )


def _default_answer_generator(pipeline: dict[str, Any]) -> str:
    """Deterministic answer from the state envelope (no model needed).

    Benchmark-fair: identical logic for every question, so a model swap
    only affects this one seam.
    """
    resolution = pipeline.get("layers", {}).get("entity_resolution", {})
    pair_verdict = resolution.get("pair_verdict")
    if pair_verdict:
        return pair_verdict
    state = pipeline.get("state_result") or {}
    status = state.get("status")
    if status == "absent":
        return "unknown"
    if status == "conflict":
        subjects = state.get("conflicting_subjects", [])
        return "conflict: " + " or ".join(subjects)
    # co-occurrence answer
    if state.get("names"):
        names = state["names"]
        return ", ".join(names) if isinstance(names, list) else str(names)
    # multi-hop artifact answer: surface the artifact id only when asked
    if state.get("evidence"):
        question = pipeline.get("question", "")
        artifact_ids = sorted({e.get("artifact_id") for e in state.get("evidence", []) if e.get("artifact_id")})
        sources = sorted({e.get("source") for e in state.get("evidence", []) if e.get("source")})
        if artifact_ids and "artifact" in question.lower():
            return f"{sources[0] if sources else 'unknown'} artifact {artifact_ids[0][:16]}"
        if sources:
            return ", ".join(sources)
    value = state.get("value") or {}
    return value.get("name") or "unknown"


class ContinuumPipeline:
    """Runs one question through the layered Continuum path."""

    def __init__(
        self,
        client: HydraDBClient,
        entity_store=None,
        answer_generator: AnswerGenerator | None = None,
    ) -> None:
        self._client = client
        self._store = entity_store
        self._generator = answer_generator or _default_answer_generator

    def answer(self, question: dict[str, Any]) -> dict[str, Any]:
        result = empty_result(
            question.get("question_id", "unknown"),
            question.get("question", ""),
        )
        question_text = question.get("question", "")
        entity = question.get("evidence_entity")
        predicate = question.get("predicate")
        category = question.get("category")

        # ---- decomposition (source-agnostic boundary) ----
        started = time.perf_counter()
        ctx = decompose_question(question)
        result["query_context"] = ctx.to_dict()
        result["latency_ms"]["decomposition"] = (time.perf_counter() - started) * 1000

        # ---- ad-hoc questions: derive entity/predicate from decomposition ----
        # Manifest rows (benchmark/gold) supply evidence_entity + predicate
        # explicitly. Ad-hoc transport questions (QueryService / Slack bot /
        # HTTP) do not, so derive them deterministically from the decomposed
        # context to keep them on the exact same reasoning path. Entity-pair
        # (ENTITY_RESOLUTION) questions deliberately keep entity=None so the
        # pair resolver runs.
        if entity is None and ctx.intent != "ENTITY_RESOLUTION" and ctx.entities:
            entity = ctx.entities[0].mention
        if predicate is None and ctx.relationships:
            predicate = ctx.relationships[0].predicate

        # ---- retrieval (candidate scoping) ----
        started = time.perf_counter()
        retrieval = self._retrieve(question_text, entity)
        result["latency_ms"]["retrieval"] = (time.perf_counter() - started) * 1000
        result["layers"]["retrieval"] = retrieval
        result["context"]["artifacts"] = retrieval.get("artifacts", 0)

        # ---- entity resolution ----
        started = time.perf_counter()
        resolution = self._resolve_entity(question_text, entity)
        result["latency_ms"]["entity_resolution"] = (time.perf_counter() - started) * 1000
        result["layers"]["entity_resolution"] = resolution
        result["resolved_entities"] = resolution.get("entities", [])
        if resolution.get("trace"):
            result["trace"].extend(resolution["trace"])

        canonical = resolution.get("canonical_key") or entity

        # ---- state resolution (uses decomposed intent + temporal) ----
        started = time.perf_counter()
        state = self._state(canonical, predicate, category, question_text, ctx)
        result["latency_ms"]["state"] = (time.perf_counter() - started) * 1000
        result["state_result"] = state
        result["status"] = state.get("status", "absent")
        result["layers"]["state"] = {"status": state.get("status")}
        result["claims_used"] = [c.get("claim_id") for c in state.get("claims", [])]
        # claims consulted: state-level claims if present, else retrieval scope
        result["context"]["claims"] = max(
            len(result["claims_used"]),
            retrieval.get("claims", 0),
        )

        if state.get("status") == "conflict":
            result["conflicts"] = state.get("conflicting_subjects", [])
        result["trace"].append(f"state: {state.get('status')} for {canonical}")

        # ---- evidence selection ----
        started = time.perf_counter()
        evidence = self._evidence(canonical, predicate)
        result["latency_ms"]["evidence_selection"] = (time.perf_counter() - started) * 1000
        result["evidence"] = evidence
        result["context"]["evidence_items"] = len(evidence)
        result["layers"]["evidence_selection"] = {"evidence_items": len(evidence)}
        # context efficiency: characters/tokens in the evidence chain
        chars = sum(len(str(item.get("source", ""))) + len(str(item.get("artifact_id", ""))) for item in evidence)
        result["context"]["characters"] = chars
        result["context"]["tokens_estimate"] = max(0, chars // 4)

        # ---- answer generation (model-agnostic seam) ----
        started = time.perf_counter()
        answer = self._generator(result)
        result["answer"] = answer
        result["latency_ms"]["total"] = sum(result["latency_ms"].values())
        result["trace"].append(f"answer: {answer}")
        return result

    # ---- layers ---------------------------------------------------------

    def _retrieve(self, question_text: str, entity: str | None) -> dict[str, Any]:
        """Candidate scoping: how many artifacts could bear on this question.

        Without the teammate's retrieval layer, this is a deterministic
        scoping based on the question's evidence entity (the manifest row
        declares it). Returns artifact/claim candidates.
        """
        if entity is None:
            return {"artifacts": 0, "claims": 0, "note": "no evidence entity in manifest"}
        claims = self._client.execute(
            "MATCH (c:Claim {object_id: $entity}) RETURN count(*) AS n",
            {"entity": entity},
        ).rows
        artifacts = self._client.execute(
            "MATCH (c:Claim {object_id: $entity})-[:SOURCED_FROM]->(a:Artifact) RETURN count(*) AS n",
            {"entity": entity},
        ).rows
        return {
            "artifacts": artifacts[0]["n"] if artifacts else 0,
            "claims": claims[0]["n"] if claims else 0,
        }

    def _resolve_entity(self, question_text: str, entity: str | None) -> dict[str, Any]:
        """Mention → canonical key via the EntityStore (or passthrough).

        For entity-resolution questions (no evidence_entity in the manifest),
        the question embeds two mentions; they are resolved as a candidate
        pair through the deterministic resolver (same logic as the e2e
        benchmark).
        """
        from continuum.entities.pairs import IdentityPair
        from continuum.entities.resolver import EntityResolver, ResolutionDecision

        if entity is not None:
            if self._store is None:
                return {
                    "entities": [entity],
                    "canonical_key": entity,
                    "trace": [f"entity resolution: passthrough ({entity})"],
                }
            payload = self._store.resolve_mention(entity)
            canonical = payload.get("entity_key")
            return {
                "entities": [canonical] if canonical else [entity],
                "canonical_key": canonical or entity,
                "trace": [f"entity resolution: {entity} -> {canonical or 'unresolved'}"],
            }

        # no evidence_entity: entity-resolution question with two mentions
        mentions = _extract_mentions(question_text)
        if len(mentions) < 2:
            return {"entities": [], "canonical_key": None, "trace": ["entity resolution: no mention pair"]}
        # Consistency with the extraction path: when an EntityStore exists
        # (graph loaded from resolved entities), both mentions resolve
        # through the SAME canonical identity the extraction produced.
        if self._store is not None:
            left = self._store.resolve_mention(mentions[0])
            right = self._store.resolve_mention(mentions[1])
            if left["status"] == "definitive" and right["status"] == "definitive":
                same = left["entity_key"] == right["entity_key"]
                return {
                    "entities": [mentions[0], mentions[1]],
                    "canonical_key": None,
                    "pair_verdict": "same" if same else "different",
                    "trace": [
                        f"entity resolution: {mentions[0]} vs {mentions[1]} -> "
                        f"{'same' if same else 'different'} (store keys "
                        f"{left['entity_key']} vs {right['entity_key']})"
                    ],
                }
        pair = _pair_with_inventory_signals(mentions, question_text)
        verdict = EntityResolver().resolve_pair(
            pair.candidate_a(),
            pair.candidate_b(),
            features=pair.merged_features(),
        )
        decision = verdict.decision
        if decision == ResolutionDecision.MERGE:
            answer_verdict = "same"
        elif decision == ResolutionDecision.KEEP_SEPARATE:
            answer_verdict = "different"
        else:
            answer_verdict = "uncertain"
        return {
            "entities": [mentions[0], mentions[1]],
            "canonical_key": None,
            "pair_verdict": answer_verdict,
            "trace": [
                f"entity resolution: {mentions[0]} vs {mentions[1]} -> {answer_verdict} "
                f"(score={verdict.score:.2f})"
            ],
        }

    def _state(
        self,
        canonical: str | None,
        predicate: str | None,
        category: str | None,
        question_text: str,
        ctx: QueryContext | None = None,
    ) -> dict[str, Any]:
        if canonical is None:
            return {"status": "absent", "value": None}
        lower = question_text.lower()
        intent = ctx.intent if ctx is not None else None

        if intent == "SOURCE_PRESENCE" or (
            category == "cross-source" and "does" in lower and "show" in lower
        ):
            return self._source_presence(canonical, predicate or "OWNS", question_text)
        if intent == "PROVENANCE" or category == "provenance" or (
            "which claim and artifact" in lower
            or "which source" in lower
            or "which artifact" in lower
            or "evidence chain" in lower
        ):
            return resolve_provenance(self._client, canonical, predicate or "OWNS")
        if intent == "CONFLICT" or category == "conflict" or (
            "conflict" in lower and "which claim and artifact" not in lower
        ):
            return resolve_conflict_state(self._client, canonical, predicate or "OWNS")
        if intent == "CO_OCCURRENCE" or ("who else" in lower or "appears in artifacts" in lower) and predicate is None:
            return self._cooccurrence(canonical)
        if intent == "DECISION":
            return resolve_provenance(self._client, canonical, predicate or "OWNS")
        if ctx is not None and ctx.temporal:
            return resolve_state_for_constraints(
                self._client, canonical, predicate or "OWNS", ctx.temporal
            )
        predicate = predicate or "OWNS"
        if category == "temporal" or "as of" in lower or "when did" in lower:
            return resolve_state_on(self._client, canonical, _default_as_of(), predicate)
        return resolve_state(self._client, canonical, predicate)

    def _source_presence(
        self,
        canonical: str,
        predicate: str,
        question_text: str,
    ) -> dict[str, Any]:
        payload = resolve_provenance(self._client, canonical, predicate)
        evidence = payload.get("evidence") or []
        lower = question_text.lower()
        mentioned = [
            name
            for name in ("slack", "gmail", "github", "linear", "jira", "confluence", "fireflies")
            if name in lower
        ]
        sources = sorted({str(item.get("source") or "").lower() for item in evidence if item.get("source")})
        if mentioned:
            sources = [s for s in sources if s in mentioned]
        handoff = "handoff" in lower
        if handoff:
            filtered = []
            for item in evidence:
                title = str(item.get("artifact_kind") or item.get("artifact_id") or "").lower()
                if "handoff" in title:
                    filtered.append(item)
                    continue
                src = str(item.get("source") or "").lower()
                if src:
                    filtered.append(item)
            if filtered:
                sources = sorted({str(item.get("source") or "").lower() for item in filtered if item.get("source")})
        payload["value"] = {"sources": sources, "name": ", ".join(s.capitalize() for s in sources)}
        payload["status"] = "definitive" if sources else "absent"
        payload["sources"] = sources
        return payload

    def _cooccurrence(self, entity: str) -> dict[str, Any]:
        """Entities co-occurring with the subject across shared artifacts."""
        rows = self._client.execute(
            """
            MATCH (c:Claim {subject_id: $entity})-[:SOURCED_FROM]->(a:Artifact),
                  (c2:Claim)-[:SOURCED_FROM]->(a)
            WHERE c2.subject_id <> $entity
            RETURN DISTINCT c2.subject_name AS name, c2.subject_id AS key
            ORDER BY name
            """,
            {"entity": entity},
        ).rows
        names = [row["name"] for row in rows if row.get("name")]
        return {"status": "definitive" if names else "absent", "value": ", ".join(names), "names": names}

    def _evidence(self, canonical: str | None, predicate: str | None) -> list[dict[str, Any]]:
        if canonical is None:
            return []
        predicate = predicate or "OWNS"
        payload = resolve_provenance(self._client, canonical, predicate)
        return payload.get("evidence", [])
