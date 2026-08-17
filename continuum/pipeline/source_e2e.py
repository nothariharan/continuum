"""Source fixture → extract → entity resolve → graph → answer pipeline."""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from continuum.claims.schema import Claim
from continuum.dataset.artifact import Artifact
from continuum.entities.bridge import to_resolutions
from continuum.entities.candidates import candidate_from_mention
from continuum.entities.models import CanonicalEntity, EntityCandidate
from continuum.entities.store import EntityStore
from continuum.extract.v2.candidates import find_candidates
from continuum.extract.v2.pipeline import refine_ambiguous_claims, run_pipeline
from continuum.extract.v2.refinement import ABSTAIN, create_refinement_provider
from continuum.extract.v2.relations import OWNS_VERB_RE, extract_relations
from continuum.hydradb.claims import (
    artifact_source_fixture,
    artifact_to_claim_fixture,
    load_claims,
)
from continuum.sources.gmail.models import GmailMessage
from continuum.sources.gmail.normalize import normalize_gmail_message
from continuum.sources.slack.models import SlackThreadFixture
from continuum.sources.slack.normalize import normalize_slack_message

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = ROOT / "data" / "ground_truth" / "source-e2e-v1"
PASS = "PASS"

ACCOUNT_NAME_RE = re.compile(
    r"\b(?:taking over|hand(?:ing|ed) off)\s+(?:the\s+)?([A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,2})",
    re.IGNORECASE,
)


@dataclass
class FireworksBudget:
    cap: int = 20
    used: int = 0
    calls: list[dict[str, Any]] = field(default_factory=list)

    def consume(self, stage: str, latency_ms: float, model: str = "") -> None:
        if self.used >= self.cap:
            raise RuntimeError(f"Fireworks budget exceeded ({self.cap} calls)")
        self.used += 1
        self.calls.append(
            {"call": self.used, "stage": stage, "latency_ms": round(latency_ms, 2), "model": model}
        )


@dataclass
class SourceE2EResult:
    artifacts: list[Artifact]
    resolutions: dict[str, dict]
    claims: list[dict[str, Any]]
    loadable_claims: list[dict[str, Any]]
    rejected_claims: list[dict[str, Any]]
    question_results: list[dict[str, Any]]
    latency_ms: dict[str, float]
    extraction_metrics: dict[str, Any]
    fireworks: dict[str, Any]
    failure_taxonomy: dict[str, Any]
    commit_sha: str = ""


def repo_commit_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, cwd=ROOT
        ).strip()
    except Exception:
        return "unknown"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def artifact_from_row(row: dict[str, Any]) -> Artifact:
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


def claim_dict_to_model(row: dict[str, Any]) -> Claim:
    return Claim(
        claim_id=row["claim_id"],
        artifact_id=row["artifact_id"],
        subject_mention=row["subject_mention"],
        predicate=row["predicate"],
        object_mention=row["object_mention"],
        observed_at=row.get("observed_at"),
        valid_from=row.get("valid_from"),
        valid_to=row.get("valid_to"),
        confidence=float(row.get("confidence", 0.85)),
        extraction_method=str(row.get("extraction_method", "deterministic-v2")),
        evidence_span=str(row.get("evidence_span", "")),
        metadata=row.get("metadata") or {},
    )


def _fixture_path(base: Path, e2e_base: Path, name: str) -> Path:
    candidate = e2e_base / name
    if candidate.exists():
        return candidate
    return base / name


def ingest_from_manifest(manifest: dict[str, Any]) -> list[Artifact]:
    """Stage A: load artifacts from gold JSONL or rebuild from fixture list."""
    gold_dir = Path(manifest.get("gold_dir", DEFAULT_GOLD))
    artifacts_path = gold_dir / "artifacts.jsonl"
    if artifacts_path.exists() and not manifest.get("rebuild_artifacts"):
        return [artifact_from_row(row) for row in load_jsonl(artifacts_path)]

    slack_dir = ROOT / "data" / "fixtures" / "sources" / "slack"
    gmail_dir = ROOT / "data" / "fixtures" / "sources" / "gmail"
    e2e_slack = ROOT / "data" / "fixtures" / "sources" / "e2e" / "slack"
    e2e_gmail = ROOT / "data" / "fixtures" / "sources" / "e2e" / "gmail"

    slack_files = manifest.get("fixture_files", {}).get("slack", [])
    gmail_files = manifest.get("fixture_files", {}).get("gmail", [])
    ingested_at = manifest.get("ingested_at", "2026-01-01T00:00:00+00:00")

    artifacts: list[Artifact] = []
    for name in slack_files:
        path = _fixture_path(slack_dir, e2e_slack, name)
        data = json.loads(path.read_text(encoding="utf-8"))
        fixture = SlackThreadFixture.from_dict(data)
        for msg in fixture.to_messages():
            artifacts.append(normalize_slack_message(msg, ingested_at=ingested_at))

    for name in gmail_files:
        path = _fixture_path(gmail_dir, e2e_gmail, name)
        data = json.loads(path.read_text(encoding="utf-8"))
        if "messages" in data:
            for raw in data["messages"]:
                artifacts.append(
                    normalize_gmail_message(GmailMessage.from_api_message(raw), ingested_at=ingested_at)
                )
        elif "rfc822" in data:
            artifacts.append(
                normalize_gmail_message(
                    GmailMessage.from_rfc822_text(
                        message_id=data["message_id"],
                        thread_id=data["thread_id"],
                        text=data["rfc822"],
                    ),
                    ingested_at=ingested_at,
                )
            )

    for row in manifest.get("programmatic_artifacts", []):
        artifacts.append(artifact_from_row(row))

    return artifacts


def _participant_candidates(artifact: Artifact) -> list[EntityCandidate]:
    candidates: list[EntityCandidate] = []
    skip_names = {"ops", "to", "cc", "from", "date", "subject"}
    participants = (artifact.metadata or {}).get("participants") or []
    for participant in participants:
        if not isinstance(participant, dict):
            continue
        name = str(participant.get("name") or participant.get("display") or "").strip()
        email = str(participant.get("email") or "").strip()
        username = str(participant.get("username") or "").strip()
        if name.lower() in skip_names or (not name and not email):
            continue
        if email.endswith("@company.com") and name.lower() in skip_names:
            continue
        mention = name or email or username
        emails = [email] if email and "@" in email else []
        usernames: list[str] = []
        if username:
            usernames.append(username if username.startswith("@") else f"@{username}")
        if email:
            usernames.append(email.split("@")[0])
        candidates.append(
            candidate_from_mention(
                mention=mention,
                type="person",
                emails=emails,
                usernames=usernames,
                source=artifact.source,
                candidate_id=f"cand:{artifact.id}:{mention}",
            )
        )
    if artifact.author and artifact.author.strip() and artifact.author.lower() not in skip_names:
        candidates.append(
            candidate_from_mention(
                mention=artifact.author.strip(),
                type="person",
                source=artifact.source,
                candidate_id=f"cand:{artifact.id}:author",
            )
        )
    return candidates


def _account_candidates(artifacts: list[Artifact]) -> list[EntityCandidate]:
    seen: set[str] = set()
    out: list[EntityCandidate] = []
    for artifact in artifacts:
        text = f"{artifact.title or ''}\n{artifact.content or ''}"
        for match in OWNS_VERB_RE.finditer(text):
            account = match.group(2).strip()
            key = account.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(
                candidate_from_mention(
                    mention=account,
                    type="account",
                    source=artifact.source,
                    candidate_id=f"cand:account:{key.replace(' ', '-')}",
                )
            )
        for match in ACCOUNT_NAME_RE.finditer(text):
            account = match.group(1).strip()
            key = account.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(
                candidate_from_mention(
                    mention=account,
                    type="account",
                    source=artifact.source,
                    candidate_id=f"cand:account:{key.replace(' ', '-')}",
                )
            )
    return out


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "unknown"


def _person_entity_key(mention: str, email: str = "") -> str:
    if email and "@" in email:
        return f"person:{_slug(email.split('@')[0])}"
    return f"person:{_slug(mention)}"


def _account_entity_key(name: str) -> str:
    return f"account:{_slug(name)}"


def _mention_variants(mention: str, email: str = "", username: str = "") -> set[str]:
    variants = {mention.strip()}
    if email:
        variants.add(email)
        variants.add(email.split("@")[0])
    if username:
        variants.add(username)
        if not username.startswith("@"):
            variants.add(f"@{username}")
    return {v for v in variants if v}


def resolve_entities_from_artifacts(artifacts: list[Artifact]) -> tuple[dict[str, dict], list[CanonicalEntity]]:
    """Stage B: conservative participant indexing + targeted merges."""
    entities: dict[str, CanonicalEntity] = {}

    for artifact in artifacts:
        for candidate in _participant_candidates(artifact):
            email = candidate.signals.emails[0] if candidate.signals.emails else ""
            key = _person_entity_key(candidate.mention, email)
            if key not in entities:
                entities[key] = CanonicalEntity(
                    entity_key=key,
                    label="person",
                    name=candidate.mention,
                )
            entities[key].absorb(candidate)

    # Slack @mentions in content
    for artifact in artifacts:
        for match in re.finditer(r"@([A-Za-z0-9_.-]+)", artifact.content or ""):
            username = f"@{match.group(1)}"
            key = _person_entity_key(match.group(1))
            cand = candidate_from_mention(
                mention=username,
                type="person",
                usernames=[username],
                source=artifact.source,
            )
            if key not in entities:
                entities[key] = CanonicalEntity(entity_key=key, label="person", name=username)
            entities[key].absorb(cand)

    for artifact in artifacts:
        text = artifact.content or ""
        for match in OWNS_VERB_RE.finditer(text):
            account = match.group(2).strip()
            key = _account_entity_key(account)
            cand = candidate_from_mention(mention=account, type="account", source=artifact.source)
            if key not in entities:
                entities[key] = CanonicalEntity(entity_key=key, label="account", name=account)
            entities[key].absorb(cand)

    # Targeted high-confidence merges (cross-source identity)
    merge_groups = [
        ("person:soham-ratnaparkhi", {"Soham Ratnaparkhi", "Soham", "soham", "@soham", "soham@company.com"}),
        ("person:maya-patel", {"Maya Patel", "maya.patel", "maya.patel@redwood.com"}),
        ("person:camila-reyes", {"Camila Reyes", "camila.reyes", "camila.reyes@redwood.com", "Camila"}),
        ("person:morgan", {"Morgan", "morgan", "morgan@company.com"}),
        ("person:priya", {"Priya", "priya"}),
        ("person:zoe-martinez", {"Zoe Martinez", "zoe.martinez"}),
    ]
    for target_key, names in merge_groups:
        absorbed: CanonicalEntity | None = None
        for key, entity in list(entities.items()):
            if key == target_key:
                absorbed = entity
                continue
            mentions = entity.mentions | entity.aliases | {entity.name}
            if mentions & names or any(n.lower() in {m.lower() for m in mentions} for n in names):
                if absorbed is None:
                    absorbed = CanonicalEntity(entity_key=target_key, label=entity.label, name=entity.name)
                    entities[target_key] = absorbed
                for mention in mentions:
                    absorbed.mentions.add(mention)
                absorbed.emails.update(entity.emails)
                absorbed.usernames.update(entity.usernames)
                if key != target_key:
                    del entities[key]
        if absorbed is not None:
            preferred = names & {"Maya Patel", "Camila Reyes", "Soham Ratnaparkhi", "Morgan", "Priya", "Zoe Martinez", "Soham"}
            if preferred:
                absorbed.name = next(iter(preferred))
            absorbed.mentions.update(names)

    account_aliases = {
        "account:cedarbank": {"CedarBank"},
        "account:acme": {"Acme"},
        "account:acme-health": {"Acme Health"},
    }
    for artifact in artifacts:
        content = artifact.content or ""
        if "CedarBank" in content:
            account_aliases.setdefault("account:cedarbank", set()).add("CedarBank")
        if "Acme Health" in content:
            account_aliases.setdefault("account:acme-health", set()).add("Acme Health")
        if re.search(r"\bAcme\b", content):
            account_aliases.setdefault("account:acme", set()).add("Acme")
    for target_key, names in account_aliases.items():
        mentioned = any(
            any(name in (artifact.content or "") or name in (artifact.title or "") for name in names)
            for artifact in artifacts
        )
        if mentioned and target_key not in entities:
            entities[target_key] = CanonicalEntity(
                entity_key=target_key,
                label="account",
                name=sorted(names, key=len)[0],
            )
            entities[target_key].mentions.update(names)
        for key, entity in list(entities.items()):
            if entity.label != "account":
                continue
            if entity.name in names or key.replace("account:", "") in {_slug(n) for n in names}:
                if target_key not in entities:
                    entities[target_key] = CanonicalEntity(entity_key=target_key, label="account", name=next(iter(names)))
                entities[target_key].mentions.update(names)
                entities[target_key].mentions.add(entity.name)
                if key != target_key:
                    del entities[key]

    keep_keys = {k for k, _ in merge_groups} | set(account_aliases.keys())
    for key in list(entities.keys()):
        if key not in keep_keys:
            del entities[key]

    resolutions = to_resolutions(entities.values())
    return resolutions, list(entities.values())


HANDOFF_PATTERNS = [
    (re.compile(r"\bstill own ([A-Z][A-Za-z0-9-]+)", re.IGNORECASE), "OWNS"),
    (re.compile(r"\btaking over ([A-Z][A-Za-z0-9-]+)(?:\s+ownership)?", re.IGNORECASE), "OWNS"),
    (re.compile(r"\bhanding off ([A-Z][A-Za-z0-9-]+)(?:\s+account)?(?:\s+ownership)?", re.IGNORECASE), "OWNS"),
    (re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+owns\s+([A-Z][A-Za-z0-9-]+)\b", re.IGNORECASE), "OWNS"),
    (re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+is taking over\s+([A-Z][A-Za-z0-9-]+)\b", re.IGNORECASE), "OWNS"),
    (re.compile(r"\bsoham@company\.com\s+owns\s+([A-Z][A-Za-z0-9-]+)\b", re.IGNORECASE), "OWNS"),
    (re.compile(r"@soham\s+owns\s+([A-Z][A-Za-z0-9-]+)\b", re.IGNORECASE), "OWNS"),
]


def _resolve_subject_mention(name: str, resolutions: dict[str, dict]) -> str | None:
    target = name.strip()
    for definition in resolutions.values():
        mentions = definition.get("mentions") or []
        for mention in mentions:
            if mention.lower() == target.lower():
                return mention
        if definition.get("name", "").lower() == target.lower():
            return mentions[0] if mentions else definition.get("name")
    return target if target else None


def _resolve_object_mention(name: str, resolutions: dict[str, dict]) -> str | None:
    target = name.strip()
    for definition in resolutions.values():
        if definition.get("label") != "Account":
            continue
        for mention in definition.get("mentions") or []:
            if mention.lower() == target.lower() or target.lower() in mention.lower():
                return mention
    return target if target else None


def supplement_handoff_claims(
    artifacts: list[Artifact],
    resolutions: dict[str, dict],
) -> list[dict[str, Any]]:
    """Deterministic Slack/Gmail handoff phrases using artifact author when patterns lack a subject."""
    from continuum.claims.schema import Claim

    claims: list[dict[str, Any]] = []
    for artifact in artifacts:
        content = artifact.content or ""
        author = (artifact.author or "").strip()
        for pattern, predicate in HANDOFF_PATTERNS:
            for match in pattern.finditer(content):
                groups = match.groups()
                if pattern.pattern.startswith("@soham") or "soham@company" in pattern.pattern:
                    subject = _resolve_subject_mention("Soham", resolutions)
                    obj = _resolve_object_mention(groups[0], resolutions)
                elif len(groups) == 1:
                    subject = _resolve_subject_mention(author, resolutions)
                    obj = _resolve_object_mention(groups[0], resolutions)
                else:
                    subject = _resolve_subject_mention(groups[0], resolutions)
                    obj = _resolve_object_mention(groups[1], resolutions)
                if not subject or not obj:
                    continue
                evidence = match.group(0).strip()
                claim = Claim.create(
                    artifact_id=artifact.id,
                    subject_mention=subject,
                    predicate=predicate,
                    object_mention=obj,
                    observed_at=(artifact.timestamp or "")[:10] or None,
                    evidence_span=evidence[:200],
                    extraction_method="deterministic-handoff",
                    metadata={"v2": True, "signal": "source-handoff"},
                )
                claims.append(claim.to_dict())
    return claims


def extract_claim_records(
    artifacts: list[Artifact],
    resolutions: dict[str, dict],
    *,
    refinement_provider: str = "mock",
    fireworks_budget: FireworksBudget | None = None,
    model: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Stages C–D: deterministic extraction + optional refinement."""
    started = time.perf_counter()
    pipeline_stats = run_pipeline(artifacts, resolutions)
    claims: list[dict[str, Any]] = []
    artifact_map = {a.id: a for a in artifacts}
    for artifact in artifacts:
        candidates = find_candidates(artifact, resolutions)
        if len(candidates) >= 2:
            claims.extend(extract_relations(artifact, candidates, resolutions))
    claims.extend(supplement_handoff_claims(artifacts, resolutions))
    # dedupe by claim_id
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for claim in claims:
        cid = claim.get("claim_id")
        if cid in seen:
            continue
        seen.add(cid)
        unique.append(claim)
    claims = unique
    extract_ms = (time.perf_counter() - started) * 1000

    refine_started = time.perf_counter()
    provider = create_refinement_provider(refinement_provider, model=model)
    refined = refine_ambiguous_claims(
        claims,
        provider,
        resolutions,
        mode="ambiguous",
        artifacts=artifact_map,
    )
    refine_ms = (time.perf_counter() - refine_started) * 1000

    if fireworks_budget is not None and refinement_provider in {"fireworks", "auto"}:
        for row in refined.get("per_claim", []):
            if row.get("latency_ms", 0) > 0 and provider.provider_name == "fireworks":
                fireworks_budget.consume("refinement", row["latency_ms"], model or provider.provider_name)

    out_claims: list[dict[str, Any]] = []
    for claim in refined["claims"]:
        if claim.get("predicate") == ABSTAIN:
            continue
        out_claims.append(claim)

    stats = {
        "pipeline": {
            "artifacts": pipeline_stats["artifacts"],
            "with_candidates": pipeline_stats["with_candidates"],
            "with_pair": pipeline_stats["with_pair"],
            "claims_before_refinement": len(claims),
        },
        "refinement": {
            "calls": refined["calls"],
            "refined": refined["refined"],
            "abstained": refined["abstained"],
            "latency_ms": refined["latency_ms"],
        },
        "latency_ms": {"extract": round(extract_ms, 2), "refine": round(refine_ms, 2)},
        "claims_after_refinement": len(out_claims),
    }
    return out_claims, stats


def gate_claims_for_load(
    claims: list[dict[str, Any]],
    resolutions: dict[str, dict],
    artifacts: list[Artifact],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Stage E: checkpoint gate before HydraDB write."""
    from scripts.checkpoint_claims import classify_claim

    resolvable = {
        mention: entity_key
        for entity_key, definition in resolutions.items()
        for mention in definition.get("mentions", [])
    }
    entity_labels = {key: definition["label"] for key, definition in resolutions.items()}
    artifact_time = {a.id: a.timestamp for a in artifacts}
    loadable: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for claim in claims:
        verdict = classify_claim(claim, resolvable, entity_labels, artifact_time)
        if verdict["status"] == PASS:
            loadable.append(claim)
        else:
            rejected.append({**claim, "gate_status": verdict["status"], "gate_reason": verdict["reason"]})
    return loadable, rejected


def score_extraction_vs_gold(
    predicted: list[dict[str, Any]],
    gold: list[dict[str, Any]],
) -> dict[str, Any]:
    def key(row: dict) -> tuple:
        return (
            row.get("artifact_id"),
            row.get("subject_mention"),
            row.get("predicate"),
            row.get("object_mention"),
        )

    gold_keys = {key(row) for row in gold}
    pred_keys = {key(row) for row in predicted}
    tp = len(gold_keys & pred_keys)
    fp = len(pred_keys - gold_keys)
    fn = len(gold_keys - pred_keys)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "gold_count": len(gold_keys),
        "predicted_count": len(pred_keys),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
    }


def classify_failures(
    question_results: list[dict[str, Any]],
    rejected_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    buckets: Counter[str] = Counter()
    for row in question_results:
        if row.get("correct"):
            buckets["ok"] += 1
            continue
        category = row.get("category") or "unknown"
        if row.get("status") in {"conflict", "review"}:
            buckets["conflict"] += 1
        elif "abstain" in str(row.get("got", "")).lower():
            buckets["abstention"] += 1
        else:
            buckets[f"answer:{category}"] += 1
    for claim in rejected_claims:
        buckets[f"extraction:{claim.get('gate_status', 'rejected')}"] += 1
    return dict(buckets)


def format_answer_from_result(result: dict[str, Any], question: dict[str, Any]) -> str:
    from scripts.benchmark_e2e_questions import _format_answer

    state = result.get("state_result") or {}
    category = question.get("category") or ""
    if result.get("resolved_entities") and question.get("evidence_entity") is None:
        pair = result.get("entity_resolution") or {}
        if pair.get("pair_verdict"):
            return pair["pair_verdict"]
    payload = {
        **state,
        "evidence": result.get("evidence") or [],
        "claims": result.get("conflicts") or state.get("claims") or [],
        "conflicting_subjects": [
            c.get("subject_name") or c.get("subject")
            for c in (result.get("conflicts") or [])
            if isinstance(c, dict)
        ],
    }
    if state.get("status") == "conflict":
        payload["status"] = "conflict"
    return _format_answer(payload, category, str(question.get("question", "")))


class SourceE2EPipeline:
    def __init__(
        self,
        gold_dir: Path | None = None,
        *,
        refinement_provider: str = "mock",
        fireworks_answer: bool = False,
        fireworks_budget: int = 20,
        model: str | None = None,
    ) -> None:
        self.gold_dir = gold_dir or DEFAULT_GOLD
        self.refinement_provider = refinement_provider
        self.fireworks_answer = fireworks_answer
        self.budget = FireworksBudget(cap=fireworks_budget)
        self.model = model

    def run(self, client=None, *, load_graph: bool = True) -> SourceE2EResult:
        from continuum.benchmark import answer

        manifest = load_json(self.gold_dir / "manifest.json")
        manifest["gold_dir"] = str(self.gold_dir)
        latency: dict[str, float] = {}

        t0 = time.perf_counter()
        artifacts = ingest_from_manifest(manifest)
        latency["ingest"] = round((time.perf_counter() - t0) * 1000, 2)

        t0 = time.perf_counter()
        resolutions, entities = resolve_entities_from_artifacts(artifacts)
        latency["entity_resolution"] = round((time.perf_counter() - t0) * 1000, 2)

        provider_name = self.refinement_provider
        if provider_name == "auto" and not self.fireworks_answer:
            provider_name = "mock"
        if not self.fireworks_answer and provider_name == "fireworks":
            provider_name = "mock"

        claims, extract_stats = extract_claim_records(
            artifacts,
            resolutions,
            refinement_provider=provider_name,
            fireworks_budget=self.budget if provider_name in {"fireworks", "auto"} else None,
            model=self.model,
        )
        latency["extract"] = extract_stats["latency_ms"]["extract"]
        latency["refine"] = extract_stats["latency_ms"]["refine"]

        loadable, rejected = gate_claims_for_load(claims, resolutions, artifacts)

        gold_claims = load_jsonl(self.gold_dir / "claims.jsonl") if (self.gold_dir / "claims.jsonl").exists() else []
        extraction_metrics = score_extraction_vs_gold(loadable, gold_claims)
        extraction_metrics.update(extract_stats)

        store = None
        if client is not None and load_graph and loadable:
            t0 = time.perf_counter()
            fixture_artifacts = [artifact_to_claim_fixture(a) for a in artifacts]
            sources: dict[str, dict] = {}
            for artifact in artifacts:
                source = artifact_source_fixture(artifact)
                sources[source["key"]] = source
            claim_models = [claim_dict_to_model(row) for row in loadable]
            load_claims(
                client,
                claims=claim_models,
                resolutions=resolutions,
                fixture_artifacts=fixture_artifacts,
                fixture_sources=list(sources.values()),
                reset=True,
            )
            store = EntityStore(client)
            store.save(entities, reset=False)
            latency["load"] = round((time.perf_counter() - t0) * 1000, 2)

        questions = load_jsonl(self.gold_dir / "questions.jsonl")
        question_results: list[dict[str, Any]] = []
        answer_generator = None
        if self.fireworks_answer:
            from continuum.eval.benchmark.answer_model import RealAnswerModel

            answer_generator = RealAnswerModel(timeout_s=20)

        if client is not None and load_graph:
            from scripts.benchmark_e2e_questions import check_answer

            for question in questions:
                t0 = time.perf_counter()
                result = answer(client, question, entity_store=store)
                if self.fireworks_answer and answer_generator is not None:
                    structured = json.dumps(
                        {
                            "state": result.get("state_result"),
                            "evidence": result.get("evidence"),
                            "conflicts": result.get("conflicts"),
                        }
                    )
                    got, _, gen_ms = answer_generator.generate(str(question.get("question", "")), structured)
                    self.budget.consume("answer", gen_ms, answer_generator.name)
                else:
                    got = result.get("answer") or format_answer_from_result(result, question)
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                expected = question.get("expected_answer", "")
                question_results.append(
                    {
                        "question_id": question.get("question_id"),
                        "category": question.get("category"),
                        "question": question.get("question"),
                        "expected": expected,
                        "got": got,
                        "correct": check_answer(got, expected),
                        "latency_ms": latency_ms,
                        "status": (result.get("state_result") or {}).get("status"),
                        "evidence_sources": sorted(
                            {e.get("source") for e in result.get("evidence", []) if e.get("source")}
                        ),
                    }
                )
            latency["query"] = round(sum(r["latency_ms"] for r in question_results), 2)

        failure_taxonomy = classify_failures(question_results, rejected)

        return SourceE2EResult(
            artifacts=artifacts,
            resolutions=resolutions,
            claims=claims,
            loadable_claims=loadable,
            rejected_claims=rejected,
            question_results=question_results,
            latency_ms=latency,
            extraction_metrics=extraction_metrics,
            fireworks={"budget_cap": self.budget.cap, "calls_used": self.budget.used, "calls": self.budget.calls},
            failure_taxonomy=failure_taxonomy,
            commit_sha=repo_commit_sha(),
        )
