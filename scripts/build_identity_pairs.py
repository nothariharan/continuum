"""Generate candidate identity pairs from mention_inventory.json and emit the
hand-labeled Phase 3 evaluation set.

Candidate sources (deterministic, seeded):
1. cross-source overlap flagged by the inventory (persons and emails —
   email-domain variants are the strongest same-person signal)
2. first-name mention vs full-name mention sharing the token
   (the ambiguous "Priya" vs "Priya Desai" family)
3. person mention vs email mention with matching local part
4. same-first-name different-full-name pairs (hard negatives, e.g. the two
   Maya's and the two Omar's)

`generate()` writes data/labels/phase3-identity-candidates.jsonl (unlabeled
pool). The LABELS table below is the manual review output — pairs hand-labeled
same / different / uncertain with the signals that justify the verdict.
Output: data/labels/phase3-identity-pairs.jsonl (the Phase 3 eval set).

This is evaluation-set preparation, not entity resolution.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data" / "extraction" / "mention_inventory.json"
CANDIDATES_OUT = ROOT / "data" / "labels" / "phase3-identity-candidates.jsonl"
LABELED_OUT = ROOT / "data" / "labels" / "phase3-identity-pairs.jsonl"


def _local_part(email: str) -> str:
    """Email local part with separators normalized to dots, so name-email
    matching treats 'marcus lin' and 'marcus.lin' as equal."""
    return email.split("@")[0].replace("_", ".").replace("-", ".").replace(" ", ".")


def _first_token(name: str) -> str:
    return name.split()[0].lower()


def generate(seed: int = 7, limit: int = 500) -> list[dict]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    entries = inventory["entries"]
    rng = random.Random(seed)

    pairs: dict[tuple[str, str], dict] = {}

    def add(a: dict, b: dict, source: str) -> None:
        key = tuple(sorted((a["normalized"], b["normalized"])))
        if key in pairs or key[0] == key[1]:
            return
        pairs[key] = {
            "a": {
                "mention": a["raw_mention"],
                "type": a["type"],
                "emails": a.get("emails", []),
                "external_ids": a.get("external_ids", []),
                "frequency": a.get("frequency", 0),
            },
            "b": {
                "mention": b["raw_mention"],
                "type": b["type"],
                "emails": b.get("emails", []),
                "external_ids": b.get("external_ids", []),
                "frequency": b.get("frequency", 0),
            },
            "candidate_source": source,
        }

    persons = [e for e in entries if e["type"] == "person"]
    emails = [e for e in entries if e["type"] == "email"]
    by_norm: dict[str, dict] = {}
    for e in persons + emails:
        by_norm.setdefault(e["normalized"], e)

    # 1. cross-source overlap (persons and emails)
    for e in persons + emails:
        for other_norm in e.get("cross_source_overlap", []):
            other = by_norm.get(other_norm)
            if other is not None:
                add(e, other, "cross-source-overlap")

    # 2. first-name vs full-name
    for e in persons:
        tokens = e["normalized"].split()
        if len(tokens) != 1:
            continue
        for f in persons:
            if len(f["normalized"].split()) >= 2 and _first_token(f["normalized"]) == tokens[0]:
                add(e, f, "first-name-vs-full-name")

    # 3. person vs email by local part
    for e in persons:
        local = _local_part(e["normalized"])
        for m in emails:
            if _local_part(m["normalized"]) == local:
                add(e, m, "name-vs-email-local-part")

    # 4. same-first-name hard negatives
    by_first: dict[str, list[dict]] = {}
    for e in persons:
        if len(e["normalized"].split()) >= 2:
            by_first.setdefault(_first_token(e["normalized"]), []).append(e)
    for first, group in by_first.items():
        if len(group) < 2:
            continue
        rng.shuffle(group)
        for a, b in zip(group[::2], group[1::2]):
            add(a, b, "same-first-name-different-people")

    result = list(pairs.values())
    rng.shuffle(result)
    return result[:limit]


LABELS = [
    # (mention_a, mention_b, label, signals, note)
    # ---- same ----
    ("ben_carter", "ben_carter@redwood.com", "same", ["email-local-part", "name-vs-email"], "username == email local part; Ben Carter's known email family"),
    ("ben_carter", "ben_carter@redwoodinference.com", "same", ["email-local-part", "name-vs-email"], "same user across Redwood domains"),
    ("Samira Patel", "Samira Patel (Redwood SE)", "same", ["exact-name", "role-qualifier"], "identical name; role suffix is context, not identity"),
    ("Hannah Lee", "Hannah Lee (PM)", "same", ["exact-name", "role-qualifier"], "identical name; role suffix"),
    ("Marcus", "marcus@redwood.ai", "same", ["email-thread", "name-vs-email"], "threads show Marcus Lin <marcus@redwood.ai>"),
    ("Diego", "Diego (Redwood SE)", "same", ["exact-first-name", "role-match"], "Diego in fireflies is the Redwood SE; role matches"),
    # ---- different ----
    ("Maya Chen", "Maya Patel (Redwood SE)", "different", ["distinct-full-names", "distinct-emails"], "two distinct Redwood people"),
    ("Samantha Holt", "Samantha Reed", "different", ["distinct-full-names", "distinct-emails"], "acmehealth.com vs finlytics.ai"),
    ("Samantha Reed", "Samantha Lee", "different", ["distinct-full-names", "distinct-emails"], "finlytics.ai vs acmecloud.com"),
    ("Ethan Cole", "Ethan Ross", "different", ["distinct-full-names"], "distinct surnames"),
    ("Daniel Park", "Daniel Carter", "different", ["distinct-full-names"], "distinct surnames"),
    ("Marcus Reed", "Marcus Li", "different", ["distinct-full-names"], "distinct surnames"),
    ("Marco Diaz", "Marco Bianchi", "different", ["distinct-full-names", "email"], "m.bianchi@pelionhealth.com is a different person"),
    ("Mina Haddad", "Mina Park (PM) - AurumX", "different", ["distinct-full-names"], "distinct surnames"),
    ("Nina Park (Product)", "Nina Petrova", "different", ["distinct-full-names"], "distinct surnames"),
    ("Lena Fischer", "Lena Ford", "different", ["distinct-full-names"], "both Redwood; distinct people"),
    ("Dana Liu", "Dana Lo", "different", ["distinct-full-names"], "distinct surnames"),
    ("Eliot Barnes", "Eliot Cho (Security)", "different", ["distinct-full-names"], "brightwell.ai vs Redwood Security"),
    ("Liam O'Reilly (CTO", "Liam O'Connor (Redwood Product)", "different", ["distinct-full-names"], "distinct people"),
    ("Ana Costa", "Ana Gomez (Product)", "different", ["distinct-full-names"], "pelionhealth.com vs Redwood"),
    ("Arjun Patel (Redwood SE)", "Arjun Desai", "different", ["distinct-full-names"], "distinct people"),
    ("Marco Alvarez", "Marco Diaz (Redwood SE)", "different", ["distinct-full-names"], "distinct people"),
    ("Marcus Kim", "Marcus Li (Redwood SE)", "different", ["distinct-full-names"], "distinct people"),
    ("Samira Khan", "Samira (Redwood CSM)", "different", ["distinct-full-names", "domain"], "samira.k@fintechco.com is customer-side"),
    ("Liam Park", "Lina Park", "different", ["distinct-full-names"], "Liam vs Lina"),
    ("Arjun Patel (Redwood SE)", "Maya Patel (Redwood SE)", "different", ["distinct-full-names"], "two Redwood SEs"),
    ("Ethan (Redwood SE)", "Evan (Redwood SE)", "different", ["distinct-first-names"], "Ethan vs Evan"),
    # ---- uncertain ----
    ("Priya", "Priya Raman", "uncertain", ["first-name-vs-full-name"], "multiple Priyas (Desai, Menon, Natarajan, Raman, Shah)"),
    ("Priya", "Priya Shah (DevOps)", "uncertain", ["first-name-vs-full-name"], "multiple Priyas; no shared signal"),
    ("Lena", "Lena Ortiz", "uncertain", ["first-name-vs-full-name"], "Lena/Lena Ortiz/Lena Ford/Lena Fischer all exist"),
    ("Lena", "Lena Fischer", "uncertain", ["first-name-vs-full-name"], "first name alone insufficient"),
    ("Lena", "Lena Torres", "uncertain", ["first-name-vs-full-name"], "first name alone insufficient"),
    ("Elena", "Elena (Lexana)", "uncertain", ["first-name", "cross-source-overlap"], "Elena/Lena overlap flagged; nickname plausible but unconfirmed"),
    ("Sarah Liu", "Sara Liu", "uncertain", ["cross-source-overlap", "fuzzy"], "two Sarah Lius exist (Redwood AE, CloudPartner); spelling variant unconfirmed"),
    ("Jordan", "Jordan Blake", "uncertain", ["first-name-vs-full-name"], "Jordan Park and Jordan Kim also exist"),
    ("Jordan", "Jordan Kim", "uncertain", ["first-name-vs-full-name"], "first name alone insufficient"),
    ("Rajiv", "Rajiv Menon (Polaris SRE)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Nina", "Nina Rivera", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Diego", "Diego Fuentes", "uncertain", ["first-name-vs-full-name"], "first name alone; Diego Ramos also exists"),
    ("Diego", "Diego Alvarez (Redwood SE)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Marco", "Marco Ruiz (Redwood SE)", "uncertain", ["first-name-vs-full-name"], "Marco Diaz also Redwood SE"),
    ("Marco", "Marco Bianchi", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Liam", "Liam Park", "uncertain", ["first-name-vs-full-name"], "Liam O'Connor also exists"),
    ("Liam", "Liam O'Connor (Auriga - Platform Eng)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Liam", "Liam Park (Redwood AE)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Lina", "Lina Torres", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Lina", "Lina Park", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Ethan", "Ethan Ross", "uncertain", ["first-name-vs-full-name"], "Ethan Cole and Ethan Park also exist"),
    ("Ethan", "Ethan Cole (Cobalt DevOps)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Ethan", "Ethan Park", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Marcus", "Marcus Reed", "uncertain", ["first-name-vs-full-name"], "Marcus Lin/Kim/Li/Reed all exist"),
    ("Eliot", "Eliot Barnes", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Damien", "Damien Ortiz (Redwood SE)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Erin", "Erin Lee (Security)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Mina", "Mina Park (PM) - AurumX", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Tom", "Tom Reed (Cobalt SRE)", "uncertain", ["first-name-vs-full-name"], "first name alone; several Toms"),
    ("Tom", "Tom Park (DevOps)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Tom", "Tom Briggs", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Daniel", "Daniel Park (Polaris ML)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Alex", "Alex Martinez (Redwood AE)", "uncertain", ["first-name-vs-full-name"], "multiple Alexes (Chen, Rivera, Kelly, Martinez)"),
    ("Aisha", "Aisha (PM)", "uncertain", ["first-name"], "first name alone"),
    ("Jared", "Jared Kim", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Jared", "Jared Kim (Redwood CSM)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Mike", "Mike O'Neill (Aurelian Dev)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Marta", "Marta Alvarez", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Carlos (CTO)", "Carlos Mendez", "uncertain", ["role-only"], "role-only mention; CTO could be Mendez but unconfirmed"),
    ("Evan", "Evan Brooks (Orion - Security)", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Lucas", "Lucas Ramirez (Head of Platform", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Arjun", "Arjun Desai", "uncertain", ["first-name-vs-full-name"], "first name alone"),
    ("Tom (Security)", "Tom Park", "uncertain", ["first-name", "role"], "first name + role, no identity signal"),
    # ---- email-family same pairs (strongest signal: local part == name, redwood domains) ----
    ("Marcus Lin", "marcus.lin@redwood.com", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("Marcus Lin", "marcus_lin@redwood.ai", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("Ben Carter", "ben.carter@redwood.com", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("Marissa Cole", "marissa_cole@redwood.com", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("Marissa Cole", "marissa.cole@redwood.com", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("Jonas Weber", "jonas_weber@redwood.com", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("Karthik Iyer", "karthik.iyer@redwood.com", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("Laura Bennett", "laura_bennett@redwood.ai", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("Rishi Malhotra", "rishi.malhotra@redwood.com", "same", ["name-vs-email", "email-local-part"], "full name matches email local part"),
    ("marcus.lin@redwood.com", "marcus_lin@redwood.ai", "same", ["email-local-part", "cross-source-overlap"], "same local part across Redwood domains"),
    ("ben.carter@redwood.com", "ben_carter@redwood.ai", "same", ["email-local-part", "cross-source-overlap"], "same local part across Redwood domains"),
    ("marissa_cole@redwood.com", "marissa.cole@redwood.com", "same", ["email-local-part", "cross-source-overlap"], "dot/underscore variant, same person"),
    ("laura_bennett@redwood.com", "laura.bennett@redwood.com", "same", ["email-local-part", "cross-source-overlap"], "dot/underscore variant, same person"),
    ("rishi.malhotra@redwood.com", "rishi_malhotra@redwood.ai", "same", ["email-local-part", "cross-source-overlap"], "dot/underscore variant across domains"),
    ("lauren_bishop@redwood.ai", "lauren_bishop@redwood.com", "same", ["email-local-part", "cross-source-overlap"], "same local part across Redwood domains"),
    ("karthik_iyer@redwood.ai", "karthik_iyer@redwood.com", "same", ["email-local-part", "cross-source-overlap"], "same local part across Redwood domains"),
    ("vanessa@redwood.com", "vanessa@redwood.ai", "same", ["email-local-part", "cross-source-overlap"], "same local part across Redwood domains"),
]


def build_labeled() -> list[dict]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    by_mention: dict[str, dict] = {}
    for entry in inventory["entries"]:
        by_mention.setdefault(entry["raw_mention"], entry)

    def detail(mention: str) -> dict:
        entry = by_mention.get(mention, {})
        return {
            "mention": mention,
            "type": entry.get("type", "?"),
            "emails": entry.get("emails", []),
            "external_ids": entry.get("external_ids", []),
            "frequency": entry.get("frequency", 0),
        }

    pairs = []
    for a_mention, b_mention, label, signals, note in LABELS:
        pairs.append(
            {
                "pair_id": f"ip-{len(pairs) + 1:03d}",
                "a": detail(a_mention),
                "b": detail(b_mention),
                "label": label,
                "signals": signals,
                "note": note,
            }
        )
    return pairs


def main(limit: int = 500) -> None:
    candidates = generate(limit=limit)
    CANDIDATES_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATES_OUT.open("w", encoding="utf-8") as handle:
        for pair in candidates:
            handle.write(json.dumps(pair, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(candidates)} candidate pairs -> {CANDIDATES_OUT}")
    print("by source:", dict(Counter(p["candidate_source"] for p in candidates)))

    labeled = build_labeled()
    with LABELED_OUT.open("w", encoding="utf-8") as handle:
        for pair in labeled:
            handle.write(json.dumps(pair, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(labeled)} labeled pairs -> {LABELED_OUT}")
    print("by label:", dict(Counter(p["label"] for p in labeled)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    main(limit=args.limit)
