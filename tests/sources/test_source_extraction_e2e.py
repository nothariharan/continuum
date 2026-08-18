"""Source → extract → graph → answer E2E integration tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from continuum.hydradb import HydraDBClient
from continuum.hydradb.health import diagnose
from continuum.pipeline.source_e2e import (
    DEFAULT_GOLD,
    SourceE2EPipeline,
    gate_claims_for_load,
    ingest_from_manifest,
    load_json,
    resolve_entities_from_artifacts,
)

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "data" / "ground_truth" / "source-e2e-v1"


def _hydra_available() -> bool:
    try:
        return diagnose().queryable
    except Exception:
        return False


pytestmark_hydradb = pytest.mark.skipif(not _hydra_available(), reason="HydraDB not running")


def test_source_e2e_extraction_metrics():
    pipeline = SourceE2EPipeline(GOLD)
    result = pipeline.run(client=None, load_graph=False)
    assert result.extraction_metrics["recall"] >= 0.5
    assert len(result.loadable_claims) >= 4


def test_source_e2e_robustness_invalid_llm():
    bad_claim = {
        "claim_id": "a" * 16,
        "artifact_id": "dsid_" + "b" * 32,
        "subject_mention": "Morgan",
        "predicate": "NOT_VALID",
        "object_mention": "Acme",
        "observed_at": "2024-10-01",
        "valid_from": None,
        "valid_to": None,
        "confidence": 0.9,
        "extraction_method": "test",
        "evidence_span": "test",
    }
    manifest = load_json(GOLD / "manifest.json")
    manifest["gold_dir"] = str(GOLD)
    artifacts = ingest_from_manifest(manifest)
    resolutions, _ = resolve_entities_from_artifacts(artifacts)
    _, rejected = gate_claims_for_load([bad_claim], resolutions, artifacts)
    assert rejected
    assert rejected[0]["gate_status"] == "INVALID_PREDICATE"


@pytest.mark.hydradb
@pytestmark_hydradb
def test_source_e2e_deterministic_vertical(client: HydraDBClient):
    pipeline = SourceE2EPipeline(GOLD, refinement_provider="mock", fireworks_answer=False)
    result = pipeline.run(client, load_graph=True)
    assert len(result.loadable_claims) >= 4
    assert result.question_results
    correct = sum(1 for row in result.question_results if row["correct"])
    assert correct >= len(result.question_results) * 0.4


@pytest.mark.hydradb
@pytestmark_hydradb
def test_source_e2e_cross_source_provenance(client: HydraDBClient):
    pipeline = SourceE2EPipeline(GOLD, refinement_provider="mock")
    result = pipeline.run(client, load_graph=True)
    cedar_q = next(row for row in result.question_results if row["question_id"] == "se2e-07")
    sources = set(cedar_q.get("evidence_sources") or [])
    assert "Slack" in sources or "Gmail" in sources


@pytest.mark.fireworks
@pytest.mark.skipif(not os.environ.get("FIREWORKS_API_KEY"), reason="FIREWORKS_API_KEY not set")
@pytest.mark.hydradb
@pytestmark_hydradb
def test_source_e2e_fireworks_smoke(client: HydraDBClient):
    pipeline = SourceE2EPipeline(
        GOLD,
        refinement_provider="fireworks",
        fireworks_answer=True,
        fireworks_budget=20,
    )
    result = pipeline.run(client, load_graph=True)
    assert result.fireworks["calls_used"] <= 20
