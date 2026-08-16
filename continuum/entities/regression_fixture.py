"""Phase 3B integration regression fixture — 24 manually-verified pairs.

Covers the taxonomy cases: email, username alias, external ID, initials,
same-name hard negative, role mailbox, functional mailbox, cross-source
identity, ambiguous person, unknown entity. Every label is hand-written.

Generated once into data/fixtures/phase3/entity-regression.jsonl.
"""

from __future__ import annotations

import json
from pathlib import Path

ROWS = [
    # ---- exact email match (SAME) ----
    {"pair_id": "er-001", "mention_a": "Ben Carter", "type_a": "person", "emails_a": ["ben.carter@redwood.com"],
     "mention_b": "ben_carter@redwood.ai", "type_b": "email", "emails_b": ["ben_carter@redwood.ai"],
     "label": "SAME_ENTITY", "notes": "exact email local-part across domains"},
    {"pair_id": "er-002", "mention_a": "Marissa Cole", "type_a": "person", "emails_a": ["marissa.cole@redwood.com"],
     "mention_b": "marissa_cole@redwood.inference.com", "type_b": "email", "emails_b": ["marissa_cole@redwood.inference.com"],
     "label": "SAME_ENTITY", "notes": "dot/underscore email variants"},
    # ---- username alias (SAME) ----
    {"pair_id": "er-003", "mention_a": "@soham", "type_a": "username", "usernames_a": ["soham"],
     "mention_b": "soham-dev", "type_b": "username", "usernames_b": ["soham-dev"],
     "label": "SAME_ENTITY", "notes": "username base match"},
    {"pair_id": "er-004", "mention_a": "sarah_csm", "type_a": "username", "usernames_a": ["sarah_csm"],
     "mention_b": "Sarah Chen", "type_b": "person",
     "label": "SAME_ENTITY", "notes": "CSM handle -> full name"},
    # ---- external ID (SAME) ----
    {"pair_id": "er-005", "mention_a": "soham-dev", "type_a": "username", "usernames_a": ["soham-dev"], "external_ids_a": ["soham-dev"],
     "mention_b": "S. Ratnaparkhi", "type_b": "person",
     "label": "SAME_ENTITY", "notes": "github handle == external id + initials"},
    {"pair_id": "er-006", "mention_a": "Marcus Lin", "type_a": "person", "emails_a": ["marcus.lin@redwood.com"], "external_ids_a": ["marcusl"],
     "mention_b": "marcus_lin", "type_b": "username", "usernames_b": ["marcus_lin"], "external_ids_b": ["marcusl"],
     "label": "SAME_ENTITY", "notes": "shared external id"},
    # ---- initials (SAME) ----
    {"pair_id": "er-007", "mention_a": "S. Ratnaparkhi", "type_a": "person",
     "mention_b": "Soham Ratnaparkhi", "type_b": "person",
     "label": "SAME_ENTITY", "notes": "initial + surname"},
    # ---- cross-source identity (SAME) ----
    {"pair_id": "er-008", "mention_a": "Jonas Weber", "type_a": "person", "emails_a": ["jonas_weber@redwood.com"],
     "mention_b": "jonas.weber@redwood.inference.com", "type_b": "email", "emails_b": ["jonas.weber@redwood.inference.com"],
     "label": "SAME_ENTITY", "notes": "email variants across redwood domains"},
    # ---- same-name hard negative (DIFFERENT) ----
    {"pair_id": "er-009", "mention_a": "Maya Chen", "type_a": "person", "emails_a": ["maya.chen@redwood.com"],
     "mention_b": "Maya Patel", "type_b": "person", "emails_b": ["maya.patel@redwood.com"],
     "label": "DIFFERENT_ENTITY", "notes": "same first name, distinct people"},
    {"pair_id": "er-010", "mention_a": "Sarah Chen", "type_a": "person", "emails_a": ["sarah.chen@redwood.com"],
     "mention_b": "Sarah Liu", "type_b": "person", "emails_b": ["sarah.liu@cloudpartner.com"],
     "label": "DIFFERENT_ENTITY", "notes": "shared first name only"},
    {"pair_id": "er-011", "mention_a": "Diego Alvarez", "type_a": "person", "emails_a": ["diego.alvarez@redwood.com"],
     "mention_b": "Diego Fuentes", "type_b": "person", "emails_b": ["diego.fuentes@acme.com"],
     "label": "DIFFERENT_ENTITY", "notes": "same first name, different surnames+emails"},
    # ---- role mailbox (DIFFERENT) ----
    {"pair_id": "er-012", "mention_a": "procurement@acme.ai", "type_a": "email", "emails_a": ["procurement@acme.ai"],
     "mention_b": "procurement@redwood.com", "type_b": "email", "emails_b": ["procurement@redwood.com"],
     "label": "DIFFERENT_ENTITY", "notes": "role mailboxes, same local part"},
    {"pair_id": "er-013", "mention_a": "support@acmehealth.com", "type_a": "email", "emails_a": ["support@acmehealth.com"],
     "mention_b": "support@finlytics.ai", "type_b": "email", "emails_b": ["support@finlytics.ai"],
     "label": "DIFFERENT_ENTITY", "notes": "support mailboxes, different orgs"},
    # ---- functional mailbox vs person (DIFFERENT) ----
    {"pair_id": "er-014", "mention_a": "billing@redwood.com", "type_a": "email", "emails_a": ["billing@redwood.com"],
     "mention_b": "Bill Ingram", "type_b": "person", "emails_b": ["bill.ingram@redwood.com"],
     "label": "DIFFERENT_ENTITY", "notes": "functional mailbox vs person with similar local part"},
    # ---- same surname, different first names (DIFFERENT) ----
    {"pair_id": "er-015", "mention_a": "Maya Chen", "type_a": "person",
     "mention_b": "Sarah Chen", "type_b": "person",
     "label": "DIFFERENT_ENTITY", "notes": "shared surname is not identity"},
    # ---- ambiguous person (UNCERTAIN) ----
    {"pair_id": "er-016", "mention_a": "Priya", "type_a": "person",
     "mention_b": "Priya Natarajan", "type_b": "person",
     "label": "UNCERTAIN", "notes": "multiple Priyas exist"},
    {"pair_id": "er-017", "mention_a": "Lena", "type_a": "person",
     "mention_b": "Lena Ortiz", "type_b": "person",
     "label": "UNCERTAIN", "notes": "first name alone"},
    {"pair_id": "er-018", "mention_a": "Ethan", "type_a": "person",
     "mention_b": "Ethan Cole", "type_b": "person",
     "label": "UNCERTAIN", "notes": "several Ethans"},
    # ---- unknown entity (ABSTAIN/absent) ----
    {"pair_id": "er-019", "mention_a": "Zephyr Unknown", "type_a": "person",
     "mention_b": "Quasar Nobody", "type_b": "person",
     "label": "UNCERTAIN", "notes": "no shared signals at all"},
    # ---- accidental token overlap (DIFFERENT) ----
    {"pair_id": "er-020", "mention_a": "Marcus Reed", "type_a": "person",
     "mention_b": "Marcus Li", "type_b": "person",
     "label": "DIFFERENT_ENTITY", "notes": "token overlap but distinct"},
    {"pair_id": "er-021", "mention_a": "Alex Chen", "type_a": "person",
     "mention_b": "Alex Martinez", "type_b": "person",
     "label": "DIFFERENT_ENTITY", "notes": "first-name token overlap only"},
    # ---- email username link (SAME) ----
    {"pair_id": "er-022", "mention_a": "Karthik Iyer", "type_a": "person", "emails_a": ["karthik.iyer@redwood.com"],
     "mention_b": "karthik_iyer", "type_b": "username", "usernames_b": ["karthik_iyer"],
     "label": "SAME_ENTITY", "notes": "email local part == username"},
    {"pair_id": "er-023", "mention_a": "Olga Petrov", "type_a": "person", "emails_a": ["olga.petrov@redwood.com"],
     "mention_b": "olga.petrov@redwood.inference.com", "type_b": "email", "emails_b": ["olga.petrov@redwood.inference.com"],
     "label": "SAME_ENTITY", "notes": "dot variants same person"},
    # ---- same first name, same email local part pattern but different people (DIFFERENT) ----
    {"pair_id": "er-024", "mention_a": "David Park", "type_a": "person", "emails_a": ["david.park@redwood.com"],
     "mention_b": "David Park", "type_b": "person", "emails_b": ["david.park@acme.com"],
     "label": "DIFFERENT_ENTITY", "notes": "identical names, different email domains; ambiguous but conservative"},
]


def write() -> None:
    out = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "phase3" / "entity-regression.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for row in ROWS:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(ROWS)} regression pairs -> {out}")


if __name__ == "__main__":
    write()
