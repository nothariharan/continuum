"""Unit tests for source E2E pipeline stages (no HydraDB)."""

from __future__ import annotations

from pathlib import Path

from continuum.pipeline.source_e2e import (
    FireworksBudget,
    SourceE2EPipeline,
    ingest_from_manifest,
    load_json,
)

GOLD = Path(__file__).resolve().parents[2] / "data" / "ground_truth" / "source-e2e-v1"


def test_ingest_is_deterministic():
    manifest = load_json(GOLD / "manifest.json")
    manifest["gold_dir"] = str(GOLD)
    first = ingest_from_manifest(manifest)
    second = ingest_from_manifest(manifest)
    assert [a.id for a in first] == [a.id for a in second]


def test_fireworks_budget_enforced():
    budget = FireworksBudget(cap=2)
    budget.consume("test", 1.0)
    budget.consume("test", 1.0)
    try:
        budget.consume("test", 1.0)
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_pipeline_records_latency_stages():
    result = SourceE2EPipeline(GOLD).run(client=None, load_graph=False)
    assert "ingest" in result.latency_ms
    assert "entity_resolution" in result.latency_ms
    assert result.failure_taxonomy is not None
