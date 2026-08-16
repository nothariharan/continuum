"""Deterministic relation extraction between candidate entities only.

Safety property: the relation extractor can connect candidates, but it can
never invent new entities. Every claim's subject and object come from
`candidates.find_candidates` output, and every claim is emitted only when a
linguistic pattern with an exact evidence span supports it.

Pattern families (v1, all evidence-spanned):
- Owner/Assigned lines: "Owner: <Person> - <task>"   (fireflies/hubspot)
- Ownership verbs:       "<Person> owns/is owner of/is taking over <Acct>"
- Assignment verbs:      "<Person> is assigned to <Acct>"
- Leadership verbs:      "<Person> leads/is leading <Acct>"
- Maintenance verbs:     "<Person> maintains/is maintaining <Acct>"
- Email thread:          redwood person + customer domain <-> account
- Attendee roles:        "<Name> (Redwood AE)" -> OWNS, "(Redwood SE)" -> MAINTAINS
- Slack CSM username:    "<name>_csm:" speaker -> OWNS the mentioned account

Predicate defaults are deliberately coarse (OWNS for ownership-type signals);
refining OWNS/MAINTAINS/LEADS from nuance is the later LLM layer. This layer
must never guess an entity that was not detected as a candidate.
"""

from __future__ import annotations

import re
from typing import Any

from continuum.claims.schema import stable_hash

from .candidates import Candidate
from .envelope import EvidenceEnvelope, build_envelope
from .timestamps import resolve_timestamps

OWNER_LINE_RE = re.compile(r"^\s*Owner:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*-", re.MULTILINE)
ASSIGNED_LINE_RE = re.compile(r"^\s*Assigned(?: to)?:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.MULTILINE)
OWNS_VERB_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:owns|is the owner of|is owner of|is taking over|takes over)\s+(?:the\s+)?([A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,3})"
)
LEADS_VERB_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:leads|is leading|is driving|drives)\s+(?:the\s+)?([A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,3})"
)
MAINTAINS_VERB_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:maintains|is maintaining)\s+(?:the\s+)?([A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,3})"
)
ASSIGNED_TO_VERB_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?i:is assigned to)\s+(?:the\s+)?([A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,3})"
)
PASSIVE_ASSIGNED_RE = re.compile(
    r"\b(?:(?:action items|items|task|work)\s+)?assigned to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
)
ATTENDEE_ROLE_RE = re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\(([^)]*?)\)")
EMAIL_FROM_RE = re.compile(r"^From:\s*.+?<([^>]+)>", re.MULTILINE)
EMAIL_TO_RE = re.compile(r"^To:\s*(.+)$", re.MULTILINE)
SLACK_CSM_SPEAKER_RE = re.compile(r"^([a-z][a-z0-9_]*_csm):\s", re.MULTILINE)

ENTITY_PAIR_RULES: dict[str, frozenset[tuple[str, str]]] = {
    "OWNS": frozenset({("Person", "Account"), ("Person", "Project")}),
    "MAINTAINS": frozenset({("Person", "Account"), ("Person", "Project"), ("Person", "Service"), ("Team", "Service")}),
    "LEADS": frozenset({("Person", "Account"), ("Person", "Project"), ("Person", "Team")}),
    "ASSIGNED_TO": frozenset({("Person", "Account"), ("Person", "Project")}),
    "REVIEWS": frozenset({("Person", "Account"), ("Person", "Project")}),
}


def pair_supported(predicate: str, subject_label: str, object_label: str) -> bool:
    return (subject_label, object_label) in ENTITY_PAIR_RULES.get(predicate, frozenset())


def _canonical_mention(entity_key: str, resolutions: dict[str, dict]) -> str:
    definition = resolutions.get(entity_key, {})
    mentions = definition.get("mentions") or []
    return str(mentions[0]) if mentions else entity_key


def _normalized_domain(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _account_domains(account_name: str) -> set[str]:
    """Plausible domains for an account name (hyphen and joined forms)."""
    base = re.sub(r"[^a-z0-9]", "", account_name.lower())
    hyphenated = re.sub(r"\s+", "-", account_name.lower())
    hyphenated = re.sub(r"[^a-z0-9-]", "", hyphenated)
    domains = {f"{base}.com", f"{hyphenated}.com", f"{base}.ai"}
    return {d for d in domains if len(d) > 8}


def _domain_of_email(email: str) -> str:
    match = re.search(r"@([\w.-]+)", email)
    return match.group(1).lower() if match else ""


def _person_role_map(envelope: EvidenceEnvelope) -> dict[str, str]:
    roles: dict[str, str] = {}
    for name, role in ATTENDEE_ROLE_RE.findall(envelope.content or ""):
        roles[name.strip()] = role.strip()
    for attendee in envelope.attendees:
        for name, role in ATTENDEE_ROLE_RE.findall(attendee):
            roles[name.strip()] = role.strip()
    return roles


def _owner_line_predicate(role: str) -> str:
    """Predicate for 'Owner: <Person> - task' lines.

    AE owns the account; SE/PM drive assigned work items; CSM owns the
    relationship; unknown roles default to OWNS (an Owner line names someone
    responsible for the account in this artifact's context).
    """
    role_lower = role.lower()
    if "se" in role_lower or "solutions engineer" in role_lower:
        return "ASSIGNED_TO"
    if "pm" in role_lower or "product manager" in role_lower:
        return "ASSIGNED_TO"
    return "OWNS"


def _attendee_role_predicate(role: str) -> str:
    """Predicate from a bare attendee role tag (no Owner line).

    AE leads the engagement; SE maintains the technical integration; CSM
    owns the relationship; PM leads.
    """
    role_lower = role.lower()
    if "ae" in role_lower or "account executive" in role_lower:
        return "LEADS"
    if "se" in role_lower or "solutions engineer" in role_lower:
        return "MAINTAINS"
    if "csm" in role_lower or "customer success" in role_lower:
        return "OWNS"
    if "pm" in role_lower or "product manager" in role_lower:
        return "LEADS"
    return "OWNS"


def _redwood_person_on_thread(envelope: EvidenceEnvelope) -> tuple[str | None, str | None]:
    """(redwood person name, customer domain) on an email thread.

    The redwood person may be From or To; the customer is the other side.
    Names may be Title Case or username-style (jasmine_liu). Returns
    (None, None) when there is no redwood side or no customer side.
    """
    content = envelope.content or ""
    from_match = EMAIL_FROM_RE.search(content)
    to_match = EMAIL_TO_RE.search(content)
    if not from_match or not to_match:
        return None, None
    from_domain = _domain_of_email(from_match.group(1))
    to_line = to_match.group(1)
    named = re.findall(r"([A-Za-z][A-Za-z_. ]*?)\s*<([^>]+)>", to_line)
    to_domains = [_domain_of_email(email) for _, email in named]

    def is_redwood(domain: str) -> bool:
        return "redwood" in domain

    if is_redwood(from_domain):
        customer = next((d for d in to_domains if not is_redwood(d)), None)
        sender = from_match.group(0)
        name_match = re.search(r"([A-Za-z][A-Za-z_. ]*?)\s*<", sender)
        return (name_match.group(1).strip() if name_match else None), customer
    redwood_to = next(((name, domain) for (name, domain), d in zip(named, to_domains) if is_redwood(d)), None)
    if redwood_to:
        return redwood_to[0], from_domain
    return None, None


def extract_relations(
    artifact,
    candidates: list[Candidate],
    resolutions: dict[str, dict],
) -> list[dict[str, Any]]:
    """Extract deterministic claims between candidates.

    Returns contract-shaped dicts (ready for validate_claim / the checkpoint).
    Returns [] when no supported pair pattern fires.
    """
    if len(candidates) < 2:
        return []
    envelope = build_envelope(artifact)
    content = envelope.content or ""
    observed_at, valid_from, valid_to, _ts_source = resolve_timestamps(envelope)

    person_candidates = [c for c in candidates if c.label == "Person"]
    account_candidates = [c for c in candidates if c.label == "Account"]
    if not person_candidates or not account_candidates:
        return []

    roles = _person_role_map(envelope)
    claims: list[dict[str, Any]] = []

    def emit(
        predicate: str,
        subject: Candidate,
        obj: Candidate,
        evidence: str,
        confidence: float,
        subject_text: str | None = None,
        object_text: str | None = None,
    ) -> None:
        if not pair_supported(predicate, subject.label, obj.label):
            return
        if not evidence or not evidence.strip():
            return
        subject_mention = subject_text or _canonical_mention(subject.entity_key, resolutions)
        object_mention = object_text or _canonical_mention(obj.entity_key, resolutions)
        claim_id = stable_hash(artifact.id, subject_mention, predicate, object_mention)
        claims.append(
            {
                "claim_id": claim_id,
                "artifact_id": artifact.id,
                "subject_mention": subject_mention,
                "predicate": predicate,
                "object_mention": object_mention,
                "observed_at": observed_at,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "confidence": confidence,
                "extraction_method": "deterministic-v2",
                "evidence_span": evidence.strip()[:500],
                "metadata": {
                    "v2": True,
                    "subject_key": subject.entity_key,
                    "object_key": obj.entity_key,
                    "signal": "pattern",
                },
            }
        )

    def subject_named(name: str) -> Candidate | None:
        name_lower = name.lower()
        for candidate in person_candidates:
            if candidate.mention.lower() == name_lower:
                return candidate
            if name_lower in candidate.mention.lower():
                return candidate
        return None

    def role_for(name: str) -> str:
        """Role lookup tolerant to full-name vs first-name mismatch."""
        if name in roles:
            return roles[name]
        first = name.split()[0] if name.split() else name
        if first in roles:
            return roles[first]
        for candidate in person_candidates:
            if candidate.mention.split()[0] == first and candidate.mention in roles:
                return roles[candidate.mention]
        return ""

    def object_named(name: str) -> Candidate | None:
        name_lower = name.lower()
        for candidate in account_candidates:
            if candidate.mention.lower() == name_lower:
                return candidate
            if name_lower in candidate.mention.lower() or candidate.mention.lower() in name_lower:
                return candidate
        return None

    # 1. Owner: / Assigned: lines (meeting notes, CRM records)
    owner_lined_pairs: set[tuple[str, str]] = set()
    for match in OWNER_LINE_RE.finditer(content):
        name = match.group(1).strip()
        subject = subject_named(name)
        if subject is None:
            continue
        for obj in account_candidates:
            predicate = _owner_line_predicate(role_for(name))
            emit(predicate, subject, obj, match.group(0), 0.78)
            owner_lined_pairs.add((subject.entity_key, obj.entity_key))

    for match in ASSIGNED_LINE_RE.finditer(content):
        name = match.group(1).strip()
        subject = subject_named(name)
        if subject is None:
            continue
        for obj in account_candidates:
            emit("ASSIGNED_TO", subject, obj, match.group(0), 0.80)

    # 2. Verb patterns with explicit subject and object text
    for pattern, predicate, confidence in (
        (OWNS_VERB_RE, "OWNS", 0.85),
        (LEADS_VERB_RE, "LEADS", 0.84),
        (MAINTAINS_VERB_RE, "MAINTAINS", 0.83),
        (ASSIGNED_TO_VERB_RE, "ASSIGNED_TO", 0.84),
    ):
        for match in pattern.finditer(content):
            subject = subject_named(match.group(1).strip())
            obj = object_named(match.group(2).strip())
            if subject is None or obj is None:
                continue
            emit(
                predicate, subject, obj, match.group(0), confidence,
                subject_text=match.group(1).strip(),
                object_text=match.group(2).strip(),
            )

    # 3. Passive assignment: "assigned to <Person>" with account context
    for match in PASSIVE_ASSIGNED_RE.finditer(content):
        name = match.group(1).strip()
        subject = subject_named(name)
        if subject is None:
            continue
        for obj in account_candidates:
            emit("ASSIGNED_TO", subject, obj, match.group(0), 0.76, subject_text=name)

    # 4. Email thread ownership: redwood person + customer domain <-> account
    redwood_name, customer_domain = _redwood_person_on_thread(envelope)
    thread_account: Candidate | None = None
    if redwood_name and customer_domain:
        subject = subject_named(redwood_name)
        if subject is not None:
            for obj in account_candidates:
                account_name = _canonical_mention(obj.entity_key, resolutions)
                account_domains = _account_domains(account_name)
                normalized_customer = _normalized_domain(customer_domain)
                if normalized_customer and any(
                    normalized_customer == _normalized_domain(d) or normalized_customer.endswith(_normalized_domain(d))
                    for d in account_domains
                ):
                    emit(
                        "OWNS", subject, obj, EMAIL_FROM_RE.search(content).group(0), 0.82,
                        subject_text=_canonical_mention(subject.entity_key, resolutions),
                        object_text=account_name,
                    )
                    thread_account = obj
                    break

    # 4b. AE-labeled people on a domain-matched thread own the account
    #     ("Looping in ... Priyom (AE)"). Evidence must show the AE label.
    if thread_account is not None:
        for name, role in roles.items():
            if "ae" not in role.lower() and "account executive" not in role.lower():
                continue
            subject = subject_named(name)
            if subject is None:
                continue
            evidence = f"{name} ({role})"
            if evidence not in content:
                continue
            emit("OWNS", subject, thread_account, evidence, 0.74)

    # 5. Attendee role tags when the account is the artifact's subject (title).
    #    Skipped for pairs already covered by an Owner line (Owner wins).
    if len(account_candidates) == 1:
        account = account_candidates[0]
        for name, role in roles.items():
            subject = subject_named(name)
            if subject is None:
                continue
            if (subject.entity_key, account.entity_key) in owner_lined_pairs:
                continue
            emit(_attendee_role_predicate(role), subject, account, f"{name} ({role})", 0.72)

    # 6. Slack CSM username: "<name>_csm:" speaker drives the mentioned account
    if envelope.source == "slack" and len(account_candidates) >= 1:
        for match in SLACK_CSM_SPEAKER_RE.finditer(content):
            username = match.group(1).lower()
            subject = next((c for c in person_candidates if c.mention.lower() == username), None)
            if subject is None:
                continue
            for obj in account_candidates:
                emit("OWNS", subject, obj, match.group(0), 0.74, subject_text=_canonical_mention(subject.entity_key, resolutions))

    # dedupe by claim_id
    seen: set[str] = set()
    out = []
    for claim in claims:
        if claim["claim_id"] in seen:
            continue
        seen.add(claim["claim_id"])
        out.append(claim)
    return out
