"""Phase 3B real-data entity integration — inventory -> resolver -> store -> query.

Pipeline:
    mention inventory
      → candidate generation
      → deterministic resolver clustering
      → CanonicalEntity with resolution provenance
      → persist to HydraDB (:Entity nodes)
      → mention -> canonical query + aliases/sources/evidence
      → claim bridge (subject/object mentions -> canonical keys)

Usage:
    python scripts/entity_resolution_integration.py [--reset]

Recorded for the Phase 3B report:
    mentions, clusters, cluster size distribution, review/abstain counts,
    store latency, query latency, claim bridge rate.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from continuum.dataset.artifact import Artifact
from continuum.entities import EntityResolver
from continuum.entities.bridge_claims import bridge_claims, summary as bridge_summary
from continuum.entities.candidates import candidate_from_mention
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "data" / "extraction" / "mention_inventory.json"
REAL_CLAIMS = ROOT / "data" / "fixtures" / "phase2b_real_claims.jsonl"
REPORT_OUT = ROOT / "data" / "metadata" / "entity_resolution_integration.json"


def _mention_shaped(raw: str) -> bool:
    text = (raw or "").strip()
    if not text or len(text) > 120 or "\n" in text:
        return False
    if any(t in text.lower() for t in ("subject:", "wrote:", "from:", "to:", "cc:")):
        return False
    return len(text.split()) <= 8


def main(reset: bool) -> dict:
    inventory = json.loads(DEFAULT_INVENTORY.read_text(encoding="utf-8"))
    entries = inventory["entries"]

    candidates = []
    excluded = 0
    for entry in entries:
        raw = entry["raw_mention"]
        if not _mention_shaped(raw):
            excluded += 1
            continue
        external_ids = [
            ext for ext in entry.get("external_ids", [])
            if ext.strip().lower() != entry.get("normalized", "").lower()
            and ext.strip().lower() != raw.lower()
        ]
        candidates.append(candidate_from_mention(
            mention=raw,
            type=entry.get("type", "person"),
            emails=entry.get("emails", []),
            external_ids=external_ids,
            frequency=entry.get("frequency", 0),
            candidate_id=f"inv:{entry.get('normalized', raw)}",
        ))

    started = time.perf_counter()
    resolver = EntityResolver()
    result = resolver.cluster(candidates)
    cluster_ms = (time.perf_counter() - started) * 1000

    merged = result["merged"]
    sizes = sorted((len(e.members) for e in merged.values()), reverse=True)

    with HydraDBClient() as client:
        store = EntityStore(client)
        started = time.perf_counter()
        saved = store.save(merged.values(), reset=reset)
        save_ms = (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        resolved = {
            m: store.resolve_mention(m)["status"]
            for m in ("@soham", "Jonas Weber", "Maya Patel", "Acme Health", "unknown-panda")
        }
        query_ms = (time.perf_counter() - started) * 1000

        # claim bridge
        claims = [json.loads(line) for line in REAL_CLAIMS.open(encoding="utf-8") if line.strip()]
        bridged = bridge_claims(store, claims)
        bridge = bridge_summary(bridged)

    report = {
        "gate": "entity-resolution-integration",
        "mentions": len(candidates),
        "excluded": excluded,
        "clusters": {
            "merged_count": len(merged),
            "cluster_sizes": sizes[:10],
            "max_cluster_size": sizes[0] if sizes else 0,
            "mentions_absorbed": sum(len(e.members) for e in merged.values()),
            "review_pairs": len(result["review"]),
            "abstained_pairs": len(result["abstained"]),
            "separate_pairs": len(result["separate"]),
        },
        "latency_ms": {
            "clustering": round(cluster_ms, 1),
            "store_save": round(save_ms, 1),
            "query_sample": round(query_ms, 1),
        },
        "mention_resolution_sample": resolved,
        "claim_bridge": bridge,
    }
    REPORT_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    report = main(args.reset)
    print(json.dumps(report, indent=2, ensure_ascii=False))
