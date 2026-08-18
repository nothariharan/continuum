"""Validation tests for the Phase 3 identity-pairs expanded scaffold."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPANDED = ROOT / "data" / "labels" / "phase3-identity-pairs-expanded.jsonl"


def test_expanded_pairs_schema_and_shape():
    rows = [json.loads(line) for line in EXPANDED.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 250
    pair_ids = [r["pair_id"] for r in rows]
    assert len(set(pair_ids)) == len(pair_ids)
    for row in rows:
        assert row["label"] in {"same", "different", "uncertain"}
        assert row["a"]["mention"] and row["b"]["mention"]
        assert "signals" in row


def test_expanded_pairs_are_scaffold_not_validated_gold():
    rows = [json.loads(line) for line in EXPANDED.read_text(encoding="utf-8").splitlines() if line.strip()]
    synthetic = [r for r in rows if "synthetic" in str(r.get("note", ""))]
    assert synthetic, "expected synthetic scaffold markers to be present"
    assert len(synthetic) >= 160  # 250 target - 87 base pairs


def test_synthetic_rows_must_be_marked():
    rows = [json.loads(line) for line in EXPANDED.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        if "synthetic" in row.get("pair_id", ""):
            assert "synthetic" in str(row.get("note", "")), f"unmarked synthetic pair: {row['pair_id']}"
