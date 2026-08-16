"""Deterministic entity-match scoring — feature interface + rule weights.

The scorer turns a candidate pair's FeatureVector into a single score in
[0, 1] plus the list of signals that fired. Features can be plugged in
later (embedding similarity, co-occurrence, graph overlap) without changing
the scoring rules — each feature is a named slot in FeatureVector.

Scoring table (deterministic, precedence first-hit-wins):
    email local-part ↔ email local-part        -> 0.97
    email local-part ↔ username base           -> 0.92   (name-vs-email)
    same source external ID                    -> 0.90
    username base match                        -> 0.88
    full-name match (>=2 tokens, initials ok)  -> 0.85
    >=2 shared name tokens                     -> 0.80
    1 shared name token                        -> 0.55   (weak)
    no evidence                                -> 0.0
    shared source overlap boosts weak scores   -> +0.05 (cap 0.6)

Thresholds are deliberately conservative: false merges are the critical
failure mode, so strong single-signal matches decide; weak signal
combinations do not accumulate into a merge.
"""

from __future__ import annotations

import re

from .models import EntityCandidate, EntityMatch, FeatureVector
from .candidates import canonical_local, normalize_tokens

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")

ROLE_SUFFIX_RE = re.compile(
    r"\s*\((?:redwood\s+)?(?:ae|se|csm|pm|sre|devops|security|product|eng(?:ineering)?|ops|cto|legal)\)\s*$",
    re.IGNORECASE,
)

# Role mailboxes are functional accounts, not people: a shared local part
# like 'procurement' or 'support' is NOT identity evidence.
ROLE_MAILBOXES = frozenset(
    {
        "procurement", "procure", "support", "security", "billing", "legal",
        "accounts", "accounting", "marketing", "sales", "it", "helpdesk",
        "no-reply", "noreply", "info", "admin", "ops", "marketplace-ops",
        "marketplace", "finance", "hr", "payments", "dev-null", "oncall",
    }
)

DEFAULT_WEIGHTS = {
    "name_similarity": 1.0,
    "email_match": 1.0,
    "email_username_match": 1.0,
    "username_match": 1.0,
    "external_id_match": 1.0,
    "source_overlap": 0.4,
    "cooccurrence": 0.3,
    "embedding_similarity": 0.6,
}


def _valid_emails(values) -> set[str]:
    """Only real emails count as identity evidence: local part + domain.

    The inventory sometimes stores '@Arun' as an 'email'; those produce an
    empty local part and would collide with every other invalid email.
    """
    return {v.lower() for v in values if EMAIL_RE.match(v)}


def _is_role_mailbox(email: str) -> bool:
    """Role mailboxes (procurement@x.com) are functional accounts."""
    local = canonical_local(email)
    return local.replace(".", "-") in ROLE_MAILBOXES or local.split(".")[0] in ROLE_MAILBOXES


def _mention_tokens(mention: str) -> set[str]:
    """Name tokens for a mention.

    An email mention contributes only its local-part tokens: domains and TLDs
    ('redwood.com', 'com') are not identity and would otherwise bridge
    unrelated clusters. Role mailboxes (procurement@x.com) contribute nothing
    — they are functional accounts, not people.
    """
    text = mention.strip()
    if EMAIL_RE.match(text):
        if _is_role_mailbox(text):
            return set()
        return normalize_tokens(text.split("@")[0])
    return normalize_tokens(ROLE_SUFFIX_RE.sub("", text))


def _name_similarity(a_tokens: set[str], b_tokens: set[str]) -> float | None:
    """Similarity over name tokens, handling initials.

    "S. Ratnaparkhi" -> {s, ratnaparkhi} vs "Soham Ratnaparkhi" -> {soham,
    ratnaparkhi}: the single-letter token 's' is the initial of 'soham', so
    it counts as a match.
    """
    if not a_tokens or not b_tokens:
        return None
    if a_tokens == b_tokens:
        return 1.0
    matched: set[str] = set()
    for token in a_tokens:
        if token in b_tokens:
            matched.add(token)
        elif len(token) == 1 and any(full.startswith(token) for full in b_tokens):
            matched.add(token)
        elif any(len(other) == 1 and token.startswith(other) for other in b_tokens):
            matched.add(token)
    if not matched:
        return 0.0
    return len(matched) / max(len(a_tokens | b_tokens), 1)


def username_base(username: str) -> str:
    """'soham-dev' -> 'soham'; 'ben_carter' -> 'ben.carter'."""
    value = username.lower().replace("_", "-").replace(".", "-").strip("-")
    return value.split("-")[0] if value else ""


def _username_match(a_users: set[str], b_users: set[str]) -> float | None:
    """Username match with base tolerance: 'soham' matches 'soham-dev'."""
    if not a_users or not b_users:
        return None
    if a_users & b_users:
        return 1.0
    for au in a_users:
        base_a = username_base(au)
        for bu in b_users:
            if base_a and username_base(bu) == base_a:
                return 1.0
    return 0.0


def _email_username_match(sa, sb) -> float | None:
    """Email local part on one side vs username base on the other."""
    local = {canonical_local(e) for e in _valid_emails(sa.emails)} | {
        canonical_local(e) for e in _valid_emails(sb.emails)
    }
    bases = {username_base(u) for u in sa.usernames} | {username_base(u) for u in sb.usernames}
    if not local or not bases:
        return None
    dot_local = {v.replace(".", "") for v in local}
    dot_bases = {v.replace(".", "") for v in bases}
    return 1.0 if (dot_local & dot_bases) else 0.0


def compute_features(
    a: EntityCandidate,
    b: EntityCandidate,
    weights: dict[str, float] | None = None,
    extra: dict[str, float] | None = None,
) -> FeatureVector:
    """Compute the deterministic feature vector for a candidate pair."""
    sa, sb = a.signals, b.signals

    a_tokens = normalize_tokens(sa.mention)
    b_tokens = normalize_tokens(sb.mention)
    name_similarity = _name_similarity(a_tokens, b_tokens)

    a_local = {canonical_local(e) for e in _valid_emails(sa.emails)}
    b_local = {canonical_local(e) for e in _valid_emails(sb.emails)}
    # Role mailboxes are functional accounts, not people: matching local
    # parts like 'procurement' must not be identity evidence.
    a_local = {e for e in a_local if not _is_role_mailbox(e)}
    b_local = {e for e in b_local if not _is_role_mailbox(e)}
    if a_local and b_local:
        email_match = 1.0 if a_local & b_local else 0.0
    else:
        email_match = None

    a_users = {u.lower() for u in sa.usernames}
    b_users = {u.lower() for u in sb.usernames}
    username_match = _username_match(a_users, b_users)

    a_ids = {i.lower() for i in sa.external_ids}
    b_ids = {i.lower() for i in sb.external_ids}
    external_id_match = 1.0 if a_ids and b_ids and a_ids & b_ids else (0.0 if a_ids and b_ids else None)

    source_overlap = None
    if sa.source and sb.source:
        source_overlap = 1.0 if sa.source == sb.source else 0.0

    return FeatureVector(
        name_similarity=name_similarity,
        email_match=email_match,
        email_username_match=_email_username_match(sa, sb),
        username_match=username_match,
        external_id_match=external_id_match,
        source_overlap=source_overlap,
        cooccurrence=(extra or {}).get("cooccurrence"),
        embedding_similarity=(extra or {}).get("embedding_similarity"),
        extra={k: v for k, v in (extra or {}).items() if k not in ("cooccurrence", "embedding_similarity")},
    )


def _shared_name_tokens(a: EntityCandidate, b: EntityCandidate) -> set[str]:
    """Shared name tokens with initial compatibility ('s' ~ 'soham').

    Role qualifiers like '(Redwood AE)' are stripped first: they are context,
    not identity — every AE mention would otherwise share 'redwood'+'ae' and
    chain-merge. Emails contribute local-part tokens only.
    """
    a_tokens = _mention_tokens(a.mention)
    b_tokens = _mention_tokens(b.mention)
    matched: set[str] = set()
    for token in a_tokens:
        if token in b_tokens:
            matched.add(token)
        elif len(token) == 1 and any(full.startswith(token) for full in b_tokens):
            matched.add(token)
        elif any(len(other) == 1 and token.startswith(other) for other in b_tokens):
            matched.add(token)
    return matched


def score_match(a: EntityCandidate, b: EntityCandidate, features: FeatureVector | None = None) -> EntityMatch:
    """Score a candidate pair deterministically.

    Signal precedence (first hit wins) — see module docstring.
    Returns an EntityMatch with score, signals, and features.
    """
    features = features or compute_features(a, b)
    signals: list[str] = []

    def add_signal(name: str) -> None:
        if name not in signals:
            signals.append(name)

    if features.email_match == 1.0:
        add_signal("email-local-part")
    if features.email_username_match == 1.0:
        add_signal("email-username")
    if features.external_id_match == 1.0:
        add_signal("external-id")
    if features.username_match == 1.0:
        add_signal("username")
    if features.source_overlap == 1.0:
        add_signal("source-overlap")

    shared = _shared_name_tokens(a, b)
    a_tokens = _mention_tokens(a.mention)
    b_tokens = _mention_tokens(b.mention)

    score = 0.0
    if features.email_match == 1.0:
        score = 0.97
    elif features.email_username_match == 1.0:
        score = 0.92
    elif features.external_id_match == 1.0:
        score = 0.90
    elif features.username_match == 1.0:
        score = 0.88
    elif shared and a_tokens and b_tokens:
        if len(a_tokens) == len(shared) and len(b_tokens) == len(shared):
            score = 0.85
            add_signal("full-name")
        elif len(shared) >= 2:
            score = 0.80
            add_signal("name-tokens")
        else:
            score = 0.55
            add_signal("name-token-single")

    if features.source_overlap == 1.0 and 0.0 < score < 0.6:
        score = min(score + 0.05, 0.6)

    return EntityMatch(a=a, b=b, features=features, score=score, signals=tuple(signals))
