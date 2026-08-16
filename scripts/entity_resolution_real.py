"""Run entity resolution over the real mention inventory (data-driven).

Consumes the teammate's mention_inventory.json entries as EntityCandidates,
clusters them with the deterministic resolver, and reports:

    mentions processed
    candidate pairs examined
    merged clusters (with members)
    review / separate / abstain counts
    graph-loadability impact: how many real-claims mentions resolve

This is the founder-side consumption point for the teammate's data —
no features.parquet needed yet; the resolver runs on the signals the
inventory already carries (emails, usernames, external IDs).

Usage:
    python scripts/entity_resolution_real.py [--inventory data/extraction/mention_inventory.json]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from continuum.entities import EntityResolver
from continuum.entities.candidates import candidate_from_mention
from continuum.entities.models import ResolutionDecision

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "data" / "extraction" / "mention_inventory.json"
REAL_CLAIMS = ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"


def _is_mention_shaped(raw: str) -> bool:
    """Exclude content blobs that are not entity mentions.

    The inventory occasionally stores thread fragments/headers as mentions;
    those match every name token inside them and create false merge hubs.
    A real mention is short, single-line, no headers/quotes.
    """
    text = (raw or "").strip()
    if not text or len(text) > 120:
        return False
    if "\n" in text or "\r" in text:
        return False
    if any(token in text.lower() for token in ("subject:", "wrote:", "from:", "to:", "cc:")):
        return False
    words = text.split()
    if len(words) > 8:
        return False
    return True


def main(inventory_path: Path) -> None:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    entries = inventory["entries"]

    candidates = []
    excluded = 0
    for entry in entries:
        raw = entry["raw_mention"]
        if not _is_mention_shaped(raw):
            excluded += 1
            continue
        # The inventory stores the mention's own raw text in external_ids for
        # some sources; a self-referential 'external id' is not identity
        # evidence. Filter it so it cannot drive false merges.
        external_ids = [
            ext for ext in entry.get("external_ids", [])
            if ext.strip().lower() != entry.get("normalized", "").lower()
            and ext.strip().lower() != raw.lower()
        ]
        candidates.append(
            candidate_from_mention(
                mention=raw,
                type=entry.get("type", "person"),
                emails=entry.get("emails", []),
                external_ids=external_ids,
                frequency=entry.get("frequency", 0),
                candidate_id=f"inv:{entry.get('normalized', raw)}",
            )
        )
    print(f"mentions: {len(candidates)}  (excluded {excluded} non-mention-shaped entries)")

    resolver = EntityResolver()
    result = resolver.cluster(candidates)

    merged = result["merged"]
    print(f"\nmerged clusters: {len(merged)}")
    print(f"review pairs: {len(result['review'])}")
    print(f"keep-separate pairs: {len(result['separate'])}")
    print(f"abstained pairs: {len(result['abstained'])}")

    members_in_cluster = sum(len(e.members) for e in merged.values())
    print(f"\nmentions absorbed into clusters: {members_in_cluster} "
          f"({round(100 * members_in_cluster / len(candidates), 1)}%)")

    sizes = Counter(len(e.members) for e in merged.values())
    print("cluster sizes:", dict(sorted(sizes.items())))

    print("\nsample clusters:")
    for key, entity in list(merged.items())[:12]:
        print(f"  {key:<32} n={len(entity.members):<3} {sorted(entity.mentions)[:5]}")

    # how many of the known-good fixture mentions resolve into a merged cluster?
    claims = [json.loads(line) for line in REAL_CLAIMS.open(encoding="utf-8") if line.strip()]
    mention_set = {c["subject_mention"].strip().lower() for c in claims} | {
        c["object_mention"].strip().lower() for c in claims
    }
    merged_mentions = {m.lower() for e in merged.values() for m in e.mentions}
    covered = mention_set & merged_mentions
    print(f"\nfixture mentions: {len(mention_set)}  covered by merged clusters: {len(covered)}")
    if mention_set - covered:
        print("  uncovered:", sorted(mention_set - covered)[:10])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    args = parser.parse_args()
    main(args.inventory)
