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

# "Display Name <email@example.com>" -> display name (email preserved elsewhere
# as provenance). Bare emails pass through unchanged.
EMAIL_IN_ANGLE_RE = re.compile(r"^(.*?)\s*<([^<>]+@[^<>]+)>\s*$")

# Horizontal whitespace only between subject tokens and the ownership verb.
# A subject must not span a newline (blocks "ownership\n\nMorgan") and must
# not start immediately after an email/mention character (blocks ".com owns",
# "@handle owns" from the generic pattern).
_HW = r"[ \t]+"
_NAME = r"[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)?"
_NO_EMAIL_EDGE = r"(?<![\w@.])"


def _normalize_person_mention(raw: str) -> str:
    """Extract a display name from a raw author/person string.

    'Maya Patel <maya.patel@redwood.com>' -> 'Maya Patel'
    'morgan <morgan@company.com>'        -> 'morgan'
    'Maya Patel'                         -> 'Maya Patel'
    '<maya@x.com>'                       -> 'maya@x.com'  (bare email preserved)
    """
    value = (raw or "").strip().strip('"').strip()
    match = EMAIL_IN_ANGLE_RE.match(value)
    if match:
        name = match.group(1).strip().strip('"').strip()
        return name if name else match.group(2).strip()
    return value


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
        raw_name = str(
            participant.get("name")
            or participant.get("display")
            or participant.get("display_name")
            or ""
        )
        name = _normalize_person_mention(raw_name)
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
        author_name = _normalize_person_mention(artifact.author.strip())
        # The author is normally already a participant (with email/username
        # signals); adding a bare author candidate would split the identity
        # into a second key. Only add it when no participant covers it.
        covered = any(
            c.signals.mention.lower() == author_name.lower()
            or author_name.lower() in c.signals.mention.lower()
            for c in candidates
        )
        if not covered:
            candidates.append(
                candidate_from_mention(
                    mention=author_name,
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


def _person_entity_key(mention: str, email: str = "", username: str = "") -> str:
    """Canonical person key from the strongest identity signal.

    email local-part > username > mention slug. Slack usernames and Gmail
    local-parts coincide for the same person, so cross-source mentions
    converge on one key without any hardcoded alias table.
    """
    if email and "@" in email:
        return f"person:{_slug(email.split('@')[0])}"
    if username:
        return f"person:{_slug(username.lstrip('@'))}"
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


def _accounts_in_text(content: str) -> set[str]:
    accounts: set[str] = set()
    for match in OWNS_VERB_RE.finditer(content):
        accounts.add(match.group(2).strip())
    for match in ACCOUNT_NAME_RE.finditer(content):
        raw = match.group(1).strip()
        words = raw.split()
        while words and words[-1].lower() in {
            "account", "ownership", "access", "keys", "management", "the",
            "from", "to", "on", "for", "of", "in", "at",
        }:
            words.pop()
        accounts.add(" ".join(words) if words else raw)
    return accounts


def resolve_entities_from_artifacts(artifacts: list[Artifact]) -> tuple[dict[str, dict], list[CanonicalEntity]]:
    """Stage B: signal-driven entity resolution — no hardcoded whitelist.

    Candidates come only from artifact signals: participants, authors,
    @mentions, and ownership/handoff objects. Canonical keys derive from the
    strongest identity signal per candidate (email local-part, then username,
    then mention slug), so cross-source aliases converge deterministically.
    No entity is deleted for "not being predeclared" — entities exist only
    because artifact signals produced them.
    """
    entities: dict[str, CanonicalEntity] = {}

    for artifact in artifacts:
        for candidate in _participant_candidates(artifact):
            email = candidate.signals.emails[0] if candidate.signals.emails else ""
            username = candidate.signals.usernames[0] if candidate.signals.usernames else ""
            key = _person_entity_key(candidate.mention, email, username)
            if key not in entities:
                entities[key] = CanonicalEntity(
                    entity_key=key,
                    label="person",
                    name=candidate.mention,
                )
            entities[key].absorb(candidate)

    # Slack @mentions in content (not email domains, not <@userid> forms)
    for artifact in artifacts:
        for match in re.finditer(r"(?<![\w.<])@([A-Za-z0-9_.-]+)", artifact.content or ""):
            username = f"@{match.group(1)}"
            key = _person_entity_key(match.group(1), username=username)
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
        for account in _accounts_in_text(artifact.content or ""):
            key = _account_entity_key(account)
            cand = candidate_from_mention(mention=account, type="account", source=artifact.source)
            if key not in entities:
                entities[key] = CanonicalEntity(entity_key=key, label="account", name=account)
            entities[key].absorb(cand)

    resolutions = to_resolutions(entities.values())
    return resolutions, list(entities.values())


HANDOFF_PATTERNS = [
    # (pattern, predicate, subject_source)
    #   author : subject is the artifact author (1 capture group = account)
    #   inline : subject is captured in the text (2 groups = subject, account)
    #   email  : subject is the email local-part before "owns" (1 group = account)
    #   handle : subject is the @handle before "owns" (1 group = account)
    (re.compile(_NO_EMAIL_EDGE + r"still own " + r"([A-Z][A-Za-z0-9-]+)", re.IGNORECASE), "OWNS", "author"),
    (re.compile(_NO_EMAIL_EDGE + r"taking over ([A-Z][A-Za-z0-9-]+)(?: ownership)?", re.IGNORECASE), "OWNS", "author"),
    (re.compile(_NO_EMAIL_EDGE + r"handing off ([A-Z][A-Za-z0-9-]+)(?: account)?(?: ownership)?", re.IGNORECASE), "OWNS", "author"),
    (re.compile(_NO_EMAIL_EDGE + r"(" + _NAME + r")" + _HW + r"owns" + _HW + r"([A-Z][A-Za-z0-9-]+)\b", re.IGNORECASE), "OWNS", "inline"),
    (re.compile(_NO_EMAIL_EDGE + r"(" + _NAME + r")" + _HW + r"is taking over" + _HW + r"([A-Z][A-Za-z0-9-]+)\b", re.IGNORECASE), "OWNS", "inline"),
    (re.compile(_NO_EMAIL_EDGE + r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+" + _HW + r"owns" + _HW + r"([A-Z][A-Za-z0-9-]+)\b", re.IGNORECASE), "OWNS", "email"),
    (re.compile(_NO_EMAIL_EDGE + r"@[A-Za-z0-9_.-]+" + _HW + r"owns" + _HW + r"([A-Z][A-Za-z0-9-]+)\b", re.IGNORECASE), "OWNS", "handle"),
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


# ---------------------------------------------------------------------------
# Effective-date extraction (B2) — deterministic, evidence-derived validity.
#
# "taking over CedarBank ownership from July 28"      -> valid_from = 2026-07-28
# "handing off CedarBank account ownership effective July 28" -> valid_to
#
# Year resolution (never guesses):
#   1. explicit year wins
#   2. date within [-7, +45] days of the artifact's observed date -> observed year
#   3. else a cross-artifact anchor year for the same account (a related
#      artifact established the year of this event) -> that year
#   4. else abstain (validity left unset) — never invent a year
# ---------------------------------------------------------------------------
_MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_MONTH_DAY = r"(" + _MONTHS + r")\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,\s*(20\d{2}))?"
EFFECTIVE_DATE_RE = re.compile(r"(?i)\b(?:effective|starting|beginning|as of|from)\s+" + _MONTH_DAY)
UNTIL_DATE_RE = re.compile(r"(?i)\b(?:until|through|till|by)\s+" + _MONTH_DAY)

_MONTH_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _parse_month_day(match: re.Match[str]) -> tuple[int, int, int | None]:
    month = _MONTH_NUM[match.group(1).lower()]
    day = int(match.group(2))
    year = int(match.group(3)) if match.group(3) else None
    return month, day, year


def _collect_effective_anchors(artifacts: list[Artifact]) -> dict[str, int]:
    """Cross-artifact year anchors: account -> year.

    A year-less effective date whose month/day falls near the artifact's
    observed date establishes that account's event year. A later artifact
    referencing the same account can then reuse it.
    """
    from datetime import date

    anchors: dict[str, int] = {}
    for artifact in artifacts:
        content = artifact.content or ""
        observed = (artifact.timestamp or "")[:10] or ""
        if not observed:
            continue
        try:
            observed_date = date.fromisoformat(observed)
        except ValueError:
            continue
        for match in list(EFFECTIVE_DATE_RE.finditer(content)) + list(UNTIL_DATE_RE.finditer(content)):
            month, day, year = _parse_month_day(match)
            if year is not None:
                continue
            try:
                candidate = date(observed_date.year, month, day)
            except ValueError:
                continue
            if -7 <= (candidate - observed_date).days <= 45:
                for account in _accounts_in_text(content):
                    anchors.setdefault(account.lower(), observed_date.year)
    return anchors


def _resolve_effective_year(
    month: int,
    day: int,
    year: int | None,
    observed_at: str | None,
    account: str,
    anchor_years: dict[str, int],
) -> str | None:
    from datetime import date

    if year is not None:
        return f"{year:04d}-{month:02d}-{day:02d}"
    anchor = anchor_years.get(account.lower()) if account else None
    observed = (observed_at or "")[:10]
    if observed:
        try:
            observed_date = date.fromisoformat(observed)
            candidate = date(observed_date.year, month, day)
        except ValueError:
            candidate = None
        if candidate is not None and -7 <= (candidate - observed_date).days <= 45:
            return candidate.isoformat()
    if anchor:
        return f"{anchor:04d}-{month:02d}-{day:02d}"
    return None


def _effective_dates(
    content: str,
    observed_at: str | None,
    account: str,
    anchor_years: dict[str, int],
) -> tuple[str | None, str | None]:
    """Return (effective_iso, until_iso) from explicit date phrases."""
    effective: str | None = None
    until: str | None = None
    match = EFFECTIVE_DATE_RE.search(content)
    if match:
        month, day, year = _parse_month_day(match)
        effective = _resolve_effective_year(month, day, year, observed_at, account, anchor_years)
    match = UNTIL_DATE_RE.search(content)
    if match:
        month, day, year = _parse_month_day(match)
        until = _resolve_effective_year(month, day, year, observed_at, account, anchor_years)
    return effective, until


def _claim_validity(
    evidence: str,
    effective: str | None,
    until: str | None,
) -> tuple[str | None, str | None]:
    """Assign valid_from/valid_to from verb semantics in the evidence."""
    lowered = evidence.lower()
    if "handing off" in lowered or "handing over" in lowered:
        return None, effective
    if "taking over" in lowered:
        return effective, None
    if "still own" in lowered:
        return None, until
    return effective, None


def supplement_handoff_claims(
    artifacts: list[Artifact],
    resolutions: dict[str, dict],
) -> list[dict[str, Any]]:
    """Deterministic Slack/Gmail handoff phrases using artifact author when patterns lack a subject."""
    from continuum.claims.schema import Claim

    anchor_years = _collect_effective_anchors(artifacts)
    claims: list[dict[str, Any]] = []
    for artifact in artifacts:
        content = artifact.content or ""
        author = _normalize_person_mention((artifact.author or "").strip())
        observed_at = (artifact.timestamp or "")[:10] or None
        for pattern, predicate, subject_source in HANDOFF_PATTERNS:
            for match in pattern.finditer(content):
                groups = match.groups()
                if subject_source == "email":
                    email = match.group(0).split()[0]
                    subject = _resolve_subject_mention(email.split("@")[0], resolutions)
                    obj = _resolve_object_mention(groups[0], resolutions)
                elif subject_source == "handle":
                    handle = match.group(0).split()[0]
                    subject = _resolve_subject_mention(handle, resolutions)
                    obj = _resolve_object_mention(groups[0], resolutions)
                elif subject_source == "inline":
                    subject = _resolve_subject_mention(groups[0], resolutions)
                    obj = _resolve_object_mention(groups[1], resolutions)
                else:
                    subject = _resolve_subject_mention(author, resolutions)
                    obj = _resolve_object_mention(groups[0], resolutions)
                if not subject or not obj:
                    continue
                evidence = match.group(0).strip()
                effective, until = _effective_dates(content, observed_at, obj or "", anchor_years)
                valid_from, valid_to = _claim_validity(evidence, effective, until)
                claim = Claim.create(
                    artifact_id=artifact.id,
                    subject_mention=subject,
                    predicate=predicate,
                    object_mention=obj,
                    observed_at=observed_at,
                    valid_from=valid_from,
                    valid_to=valid_to,
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


ENTITY_NODE_LABELS = ("Person", "Account", "Project", "Service", "Team")


def wipe_for_entities(client, resolutions: dict[str, dict]) -> None:
    """Entity-scoped graph cleanup across ALL id ranges (B4 hermeticity).

    The state/provenance queries match claims by entity key, not id range,
    so a reset scoped to one id range can leave other-range claims about the
    same entities behind (e.g. phase1 synthetic claims about account:acme),
    silently corrupting answers. This wipes every claim referencing the
    loaded entities plus their entity nodes, then verifies the wipe — a
    failed cleanup raises instead of running a compromised graph.
    """
    for key in resolutions:
        client.execute("MATCH (c:Claim {object_id: $key}) DETACH DELETE c", {"key": key})
        client.execute("MATCH (c:Claim {subject_id: $key}) DETACH DELETE c", {"key": key})
    for key in resolutions:
        for label in ENTITY_NODE_LABELS:
            client.execute(f"MATCH (n:{label} {{key: $key}}) DETACH DELETE n", {"key": key})
    leftover = 0
    for key in resolutions:
        rows = client.execute("MATCH (c:Claim {object_id: $key}) RETURN count(*) AS n", {"key": key}).rows
        leftover += int(rows[0]["n"])
        rows = client.execute("MATCH (c:Claim {subject_id: $key}) RETURN count(*) AS n", {"key": key}).rows
        leftover += int(rows[0]["n"])
    if leftover:
        raise RuntimeError(f"entity-scoped wipe left {leftover} claim(s); refusing to load on dirty graph")


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
        pair = (result.get("layers") or {}).get("entity_resolution") or {}
        if pair.get("pair_verdict"):
            return pair["pair_verdict"]
    payload = {
        **state,
        "evidence": result.get("evidence") or [],
        "claims": state.get("claims") or [],
        "conflicting_subjects": [
            c.get("subject_name") or c.get("subject")
            for c in (state.get("claims") or [])
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
            wipe_for_entities(client, resolutions)
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
                    got = format_answer_from_result(result, question) or result.get("answer") or "unknown - abstain"
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
