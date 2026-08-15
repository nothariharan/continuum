"""Entity-resolution prep inventory from extracted mentions."""

from __future__ import annotations

from collections import defaultdict

from rapidfuzz import fuzz

from .schemas import Mention, normalize_mention_text


def build_mention_inventory(mentions: list[Mention]) -> list[dict]:
    buckets: dict[tuple[str, str], dict] = {}

    for mention in mentions:
        normalized = normalize_mention_text(mention.raw_text)
        key = (normalized, mention.type)
        if key not in buckets:
            buckets[key] = {
                "raw_mention": mention.raw_text,
                "normalized": normalized,
                "type": mention.type,
                "sources": set(),
                "external_ids": set(),
                "emails": set(),
                "usernames": set(),
                "artifact_ids": set(),
                "frequency": 0,
            }
        bucket = buckets[key]
        bucket["sources"].add(mention.source)
        bucket["artifact_ids"].add(mention.artifact_id)
        bucket["frequency"] += 1
        if mention.source_identity:
            if mention.type == "email" or "@" in mention.source_identity:
                bucket["emails"].add(mention.source_identity)
            elif mention.source_identity.startswith("@"):
                bucket["usernames"].add(mention.source_identity)
            else:
                bucket["external_ids"].add(mention.source_identity)

    entries = []
    normalized_keys = list(buckets.keys())
    for (normalized, mtype), bucket in buckets.items():
        overlaps: set[str] = set()
        for other_norm, other_type in normalized_keys:
            if other_type != mtype or other_norm == normalized:
                continue
            if fuzz.token_sort_ratio(normalized, other_norm) >= 85:
                overlaps.add(other_norm)
        entries.append(
            {
                "raw_mention": bucket["raw_mention"],
                "normalized": bucket["normalized"],
                "type": bucket["type"],
                "sources": sorted(bucket["sources"]),
                "external_ids": sorted(bucket["external_ids"]),
                "emails": sorted(bucket["emails"]),
                "usernames": sorted(bucket["usernames"]),
                "artifact_ids": sorted(bucket["artifact_ids"]),
                "frequency": bucket["frequency"],
                "cross_source_overlap": sorted(overlaps),
            }
        )

    entries.sort(key=lambda row: (-row["frequency"], row["normalized"]))
    return entries


def aggregate_cross_source_signals(mentions: list[Mention]) -> dict[str, int]:
    by_source: dict[str, set[str]] = defaultdict(set)
    for mention in mentions:
        by_source[mention.source].add(normalize_mention_text(mention.raw_text))
    overlap_count = 0
    sources = list(by_source)
    for i, src_a in enumerate(sources):
        for src_b in sources[i + 1 :]:
            overlap_count += len(by_source[src_a] & by_source[src_b])
    return {"sources": len(sources), "cross_source_overlap_pairs": overlap_count}
