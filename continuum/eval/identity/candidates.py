"""Stratified identity-pair candidate generation and gold label assembly."""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_identity_pairs import INVENTORY, LABELS, generate  # noqa: E402

from .schema import (
    LEGACY_LABEL_MAP,
    IdentityPairRow,
    MentionSide,
    normalize_difficulty_tags,
    pair_key,
)

# Additional hard-case labels beyond the legacy Phase 3 table (~87 pairs).
HARD_CASE_LABELS: list[tuple[str, str, str, list[str], str, str]] = [
    # initials / full name
    (
        "S. Ratnaparkhi",
        "Soham Ratnaparkhi",
        "same",
        ["initials", "full_name"],
        "Single-letter initial matches full first name with shared surname",
        "initials-full-name",
    ),
    # username aliases (fixture-style; usernames injected in detail())
    (
        "@soham",
        "soham-dev",
        "same",
        ["username_alias", "username_base"],
        "Username base match: @soham and soham-dev",
        "username-alias",
    ),
    # role mailbox vs person — must not merge
    (
        "procurement@redwood.com",
        "Marcus Lin",
        "different",
        ["role_mailbox", "functional_account"],
        "Procurement mailbox is not Marcus Lin",
        "role-mailbox-vs-person",
    ),
    (
        "support@redwood.com",
        "Marcus Lin",
        "different",
        ["role_mailbox", "functional_account"],
        "Support mailbox is not an individual person",
        "role-mailbox-vs-person",
    ),
    (
        "procurement@redwood.com",
        "procurement@medcord.com",
        "different",
        ["role_mailbox", "cross_domain"],
        "Same local part but different customer procurement desks",
        "functional-account-cross-domain",
    ),
    # ticket-key overlap tail
    (
        "INC-2026",
        "INC-2029",
        "uncertain",
        ["ticket_key", "cross_source_overlap"],
        "Related incident keys flagged as overlapping but distinct tickets",
        "ticket-key-overlap",
    ),
    (
        "INC-2026",
        "INV-2026",
        "uncertain",
        ["ticket_key", "fuzzy"],
        "Inventory cross-source overlap between INC-2026 and INV-2026",
        "ticket-key-fuzzy",
    ),
    # cross-source nickname
    (
        "Elena",
        "Lena",
        "uncertain",
        ["cross_source", "nickname"],
        "Elena/Lena cross-source overlap; nickname plausible but unconfirmed",
        "cross-source-nickname",
    ),
    # functional accounts across domains
    (
        "support@redwood.com",
        "support@redwood.ai",
        "uncertain",
        ["role_mailbox", "cross_source"],
        "Support desk may span domains but could be distinct routing aliases",
        "functional-cross-domain",
    ),
    # shared-token false positives
    (
        "Ethan (Redwood SE)",
        "Evan (Redwood SE)",
        "different",
        ["shared_token", "distinct_first_names"],
        "Shared Redwood SE role suffix; Ethan vs Evan are different people",
        "shared-token-false-positive",
    ),
    (
        "Arjun Patel (Redwood SE)",
        "Maya Patel (Redwood SE)",
        "different",
        ["shared_token", "distinct_full_names"],
        "Shared Redwood SE + Patel surname; distinct people",
        "shared-token-false-positive",
    ),
    # first-name hard negatives / ambiguity
    (
        "Maya",
        "Maya Chen",
        "uncertain",
        ["first_name_vs_full_name"],
        "First name alone insufficient; Maya Chen is one of several Mayas",
        "first-name-vs-full-name",
    ),
    (
        "Marcus",
        "Marcus Lin",
        "uncertain",
        ["first_name_vs_full_name"],
        "Marcus is ambiguous; Marcus Lin is one specific person",
        "first-name-vs-full-name",
    ),
    # cross-source email normalization (same person)
    (
        "stephanie_nguyen@redwood.ai",
        "stephanie.nguyen@redwood.com",
        "same",
        ["email_local_part", "cross_source"],
        "Cross-source email variants with matching local part on Redwood domains",
        "cross-source-email",
    ),
    # email dot vs underscore (already covered in legacy; add cross-company hard negative)
    (
        "marcus.lin@redwood.com",
        "marcus.li@pelionhealth.com",
        "different",
        ["email_local_part", "cross_domain"],
        "Similar local parts across unrelated domains",
        "email-local-part-hard-negative",
    ),
    (
        "Maya",
        "Maya Patel (Redwood SE)",
        "uncertain",
        ["first_name_vs_full_name", "shared_token"],
        "First name alone insufficient; Maya Patel is one of several Mayas",
        "first-name-vs-full-name",
    ),
    (
        "Samira (Redwood CSM)",
        "Samira Khan",
        "different",
        ["shared_token", "distinct_emails"],
        "Shared first name + Redwood role; customer-side Samira Khan is distinct",
        "cross-org-surname",
    ),
    (
        "ben_carter",
        "ben.carter@redwood.inference.com",
        "same",
        ["email_local_part", "username"],
        "Username aligns with dotted email local part on Redwood domain",
        "username-email-local-part",
    ),
    (
        "Priya",
        "Priya Desai",
        "uncertain",
        ["first_name_vs_full_name"],
        "Multiple Priyas in corpus; first name alone insufficient",
        "first-name-vs-full-name",
    ),
]

USERNAME_OVERRIDES: dict[str, list[str]] = {
    "@soham": ["soham"],
    "soham-dev": ["soham-dev"],
}


def load_inventory() -> dict[str, dict]:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    by_mention: dict[str, dict] = {}
    for entry in payload["entries"]:
        by_mention.setdefault(entry["raw_mention"], entry)
    return by_mention


def mention_side(mention: str, inventory: dict[str, dict]) -> MentionSide:
    entry = inventory.get(mention, {})
    usernames = list(entry.get("usernames") or [])
    usernames.extend(USERNAME_OVERRIDES.get(mention, []))
    return MentionSide(
        mention=mention,
        type=str(entry.get("type", "person")),
        emails=tuple(entry.get("emails") or []),
        usernames=tuple(dict.fromkeys(usernames)),
        external_ids=tuple(entry.get("external_ids") or []),
        sources=tuple(entry.get("sources") or []),
        frequency=int(entry.get("frequency") or 0),
    )


def _row_from_label_tuple(
    pair_id: str,
    a_mention: str,
    b_mention: str,
    legacy_label: str,
    signals: list[str],
    note: str,
    candidate_source: str,
    inventory: dict[str, dict],
) -> IdentityPairRow:
    return IdentityPairRow(
        pair_id=pair_id,
        a=mention_side(a_mention, inventory),
        b=mention_side(b_mention, inventory),
        label=LEGACY_LABEL_MAP[legacy_label],
        difficulty_tags=normalize_difficulty_tags(signals),
        label_rationale=note,
        candidate_source=candidate_source,
    )


def build_identity_pairs_v1() -> list[IdentityPairRow]:
    inventory = load_inventory()
    rows: list[IdentityPairRow] = []
    seen: set[tuple[str, str]] = set()

    def add_row(row: IdentityPairRow) -> None:
        key = pair_key(row.a.mention, row.b.mention)
        if key in seen:
            return
        seen.add(key)
        rows.append(row)

    for a_mention, b_mention, legacy_label, signals, note in LABELS:
        add_row(
            _row_from_label_tuple(
                pair_id=f"ip-{len(rows) + 1:03d}",
                a_mention=a_mention,
                b_mention=b_mention,
                legacy_label=legacy_label,
                signals=list(signals),
                note=note,
                candidate_source="legacy-phase3-labels",
                inventory=inventory,
            )
        )

    for a_mention, b_mention, legacy_label, signals, note, source in HARD_CASE_LABELS:
        add_row(
            _row_from_label_tuple(
                pair_id=f"ip-{len(rows) + 1:03d}",
                a_mention=a_mention,
                b_mention=b_mention,
                legacy_label=legacy_label,
                signals=list(signals),
                note=note,
                candidate_source=source,
                inventory=inventory,
            )
        )

    for index, row in enumerate(rows, start=1):
        row.pair_id = f"ip-{index:03d}"

    return rows


def generate_extended_candidates(seed: int = 7, limit: int = 500) -> list[dict]:
    """Extend legacy candidate pool with hard-case buckets."""
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    entries = inventory["entries"]
    rng = random.Random(seed)
    pairs: dict[tuple[str, str], dict] = {}

    def add(a: dict, b: dict, source: str) -> None:
        key = tuple(sorted((a["normalized"], b["normalized"])))
        if key in pairs or key[0] == key[1]:
            return
        pairs[key] = {
            "a": _candidate_side(a),
            "b": _candidate_side(b),
            "candidate_source": source,
        }

    for pair in generate(seed=seed, limit=limit):
        key = pair_key(pair["a"]["mention"], pair["b"]["mention"])
        pairs[key] = pair

    role_mailboxes = [e for e in entries if e["type"] == "email" and e["normalized"].startswith("procurement@")]
    persons = [e for e in entries if e["type"] == "person" and len(e["normalized"].split()) >= 2]
    for mailbox in role_mailboxes[:5]:
        for person in persons[:20]:
            if person["normalized"].split()[0] not in mailbox["normalized"]:
                add(mailbox, person, "role-mailbox-vs-person")

    tickets = [e for e in entries if e["type"] == "ticket"]
    for ticket in tickets:
        for other_norm in ticket.get("cross_source_overlap", []):
            other = next((e for e in entries if e["normalized"] == other_norm), None)
            if other is not None:
                add(ticket, other, "ticket-key-overlap")

    org_tokens = ("redwood", "finance", "security")
    token_hits = [e for e in persons if any(token in e["normalized"] for token in org_tokens)]
    rng.shuffle(token_hits)
    for a, b in zip(token_hits[::2], token_hits[1::2]):
        add(a, b, "shared-token-false-positive")

    result = list(pairs.values())
    rng.shuffle(result)
    return result[:limit]


def _candidate_side(entry: dict) -> dict:
    return {
        "mention": entry["raw_mention"],
        "type": entry["type"],
        "emails": entry.get("emails", []),
        "usernames": entry.get("usernames", []),
        "external_ids": entry.get("external_ids", []),
        "sources": entry.get("sources", []),
        "frequency": entry.get("frequency", 0),
    }


def label_distribution(rows: list[IdentityPairRow]) -> dict[str, int]:
    return dict(Counter(row.label for row in rows))
