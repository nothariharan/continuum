"""Real entity -> claim -> graph end-to-end fixture (Phase 3B validation).

The cross-source identity story:

    Slack:   "@soham" owns Acme          (mention: @soham, username soham)
    Gmail:   "S. Ratnaparkhi" discussed  (mention: S. Ratnaparkhi)
    GitHub:  "soham-dev" opened PR       (mention: soham-dev, external id)

Both mentions resolve to canonical person:soham via the resolver+store.
A claim whose subject is "@soham" bridges to person:soham, so a
"who owns Acme" question resolves through the canonical entity.

Pipeline demonstrated:
    mention -> identity resolution -> canonical entity -> claim -> state

Usage:
    python scripts/entity_to_graph_fixture.py [--reset]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from continuum.claims.schema import Claim
from continuum.entities import EntityResolver
from continuum.entities.bridge_claims import bridge_claim
from continuum.entities.candidates import candidate_from_mention
from continuum.entities.store import EntityStore
from continuum.hydradb import HydraDBClient
from continuum.hydradb.claims import load_claims as load_claims_graph
from continuum.query import resolve_provenance, resolve_state

ROOT = Path(__file__).resolve().parents[1]


def build_canonical_soham() -> dict:
    """Cluster the cross-source soham mentions into one canonical entity."""
    resolver = EntityResolver()
    mentions = [
        candidate_from_mention("@soham", type="person", usernames=["soham"], source="slack"),
        candidate_from_mention("S. Ratnaparkhi", type="person", source="gmail"),
        candidate_from_mention("soham-dev", type="person", usernames=["soham-dev"], external_ids=["soham-dev"], source="github"),
        candidate_from_mention("soham@company.com", type="email", emails=["soham@company.com"], source="gmail"),
    ]
    result = resolver.cluster(mentions)
    merged = {k: v for k, v in result["merged"].items() if "soham" in k.lower() or "ratnaparkhi" in k.lower()}
    return merged


def main(reset: bool) -> dict:
    canonical = build_canonical_soham()
    print("canonical entities:", {k: sorted(e.mentions) for k, e in canonical.items()})

    # Persist canonical entities, resolve mentions
    with HydraDBClient() as client:
        store = EntityStore(client)
        store.save(canonical.values(), reset=reset)

        for mention in ("@soham", "S. Ratnaparkhi", "soham-dev", "soham@company.com"):
            payload = store.resolve_mention(mention)
            print(f"  resolve {mention:<18} -> {payload['entity_key']}")

        # A claim with the slack mention as subject, referencing a real
        # artifact already in the graph (the 360-artifact sample).
        claim = {
            "claim_id": "claim:soham-owns-acme",
            "artifact_id": "dsid_2479a77669e042b9b8e5ba51c31e7ea2",
            "subject_mention": "@soham",
            "predicate": "OWNS",
            "object_mention": "Acme",
            "observed_at": "2026-07-29T00:00:00",
            "valid_from": "2026-07-29T00:00:00",
            "valid_to": None,
            "confidence": 0.9,
            "extraction_method": "hand-written",
            "evidence_span": "@soham owns Acme",
            "metadata": {"fixture": "phase3b-e2e"},
        }
        bridged = bridge_claim(store, claim)
        print("\nbridged claim:")
        print(f"  subject {bridged['subject_mention']!r} -> {bridged['subject_entity']} "
              f"({bridged['subject_resolved']})")
        print(f"  object  {bridged['object_mention']!r} -> {bridged['object_entity']} "
              f"({bridged['object_resolved']})  status={bridged['resolution_status']}")

        # Load the claim into the graph with a resolution map derived from the
        # canonical entity, so the canonical key becomes the graph entity key.
        resolutions = {
            "person:soham": {
                "name": "Soham Ratnaparkhi",
                "label": "Person",
                "mentions": ["@soham", "S. Ratnaparkhi", "soham-dev", "soham@company.com"],
                "aliases": ["soham", "soham-dev"],
            },
            "account:acme": {
                "name": "ACME",
                "label": "Account",
                "mentions": ["Acme"],
                "aliases": ["acme"],
            },
        }
        claim_obj = Claim(
            claim_id=claim["claim_id"], artifact_id=claim["artifact_id"],
            subject_mention="@soham", predicate="OWNS", object_mention="Acme",
            observed_at="2026-07-29T00:00:00", valid_from="2026-07-29T00:00:00",
            valid_to=None, confidence=0.9, extraction_method="hand-written",
            evidence_span="@soham owns Acme", metadata={"fixture": "phase3b-e2e"},
        )
        result = load_claims_graph(client, claims=[claim_obj], resolutions=resolutions, reset=reset)

        started = time.perf_counter()
        state = resolve_state(client, "account:acme")
        state_ms = (time.perf_counter() - started) * 1000
        provenance = resolve_provenance(client, "account:acme")

        print("\ngraph load:", {k: v for k, v in result.__dict__.items() if k in ("claims_written", "mismatches", "entities", "relationships")})
        print("state:", json.dumps(state, ensure_ascii=False)[:200], f"({round(state_ms, 2)} ms)")
        print("provenance status:", provenance["status"], "| evidence:", len(provenance.get("evidence", [])))
        return {
            "canonical": {k: sorted(e.mentions) for k, e in canonical.items()},
            "bridged_subject": bridged["subject_entity"],
            "bridged_status": bridged["resolution_status"],
            "state": state,
            "provenance_status": provenance["status"],
            "state_latency_ms": round(state_ms, 2),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    report = main(args.reset)
    (ROOT / "data" / "metadata" / "entity_to_graph_fixture.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
