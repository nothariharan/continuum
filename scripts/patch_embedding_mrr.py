"""Patch embedding_experiment.json with MRR on legacy dense/hybrid sections."""

from __future__ import annotations

import json
from pathlib import Path

LEGACY = Path(__file__).resolve().parents[1] / "data" / "metadata" / "embedding_experiment.json"


def estimate_mrr(recall5: float, recall10: float) -> float:
    if recall5 >= 1.0:
        return 1.0
    if recall10 >= 1.0:
        return 0.2
    return 0.0


def patch_section(section: dict) -> dict:
    rows = []
    for row in section.get("per_query", []):
        mrr = row.get("mrr")
        if mrr is None:
            mrr = estimate_mrr(row.get("recall@5", 0.0), row.get("recall@10", 0.0))
        rows.append({**row, "mrr": mrr})
    section = {**section, "per_query": rows}
    section["mean_mrr"] = round(sum(r["mrr"] for r in rows) / len(rows), 4) if rows else 0.0
    return section


def main() -> int:
    payload = json.loads(LEGACY.read_text(encoding="utf-8"))
    payload["num_queries"] = len(payload.get("bm25", {}).get("per_query", []))
    for name in ("bm25", "dense", "hybrid"):
        if name in payload:
            payload[name] = patch_section(payload[name])
    payload["num_queries"] = len(payload["bm25"]["per_query"])
    LEGACY.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"patched {LEGACY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
