"""Versioned extraction evaluation runs against Gold Benchmark v1."""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import resource  # Unix-only; optional (Windows falls back to tracemalloc)
except ImportError:  # pragma: no cover - Windows
    resource = None

from continuum.dataset.artifact import Artifact
from continuum.eval.failures import build_failure_corpus
from continuum.eval.gold_v1 import GoldBenchmark, git_commit_sha, load_gold_benchmark
from continuum.eval.metrics import (
    score_gold_claims_abstention,
    score_gold_claims_by_predicate,
    score_gold_claims_strict,
    score_gold_mentions,
)
from continuum.extract.claim import extract_claims
from continuum.extract.llm_client import llm_available, llm_model_name, load_local_env
from continuum.extract.mention import extract_mentions
from continuum.extract.schemas import claim_to_dict, mention_to_dict, write_jsonl

PROMPT_VERSION = "extract-v2-gapfill-20260816"
DEFAULT_GOLD_ROOT = Path(__file__).resolve().parents[2] / "data" / "ground_truth" / "v1"
DEFAULT_EVAL_ROOT = Path(__file__).resolve().parents[2] / "data" / "evals"


@dataclass
class LLMRunStats:
    model_calls: int = 0
    total_inference_ms: float = 0.0

    @property
    def avg_inference_ms(self) -> float:
        if not self.model_calls:
            return 0.0
        return round(self.total_inference_ms / self.model_calls, 2)


_LLM_STATS = LLMRunStats()


def reset_llm_stats() -> None:
    global _LLM_STATS
    _LLM_STATS = LLMRunStats()


def record_llm_call(duration_ms: float) -> None:
    _LLM_STATS.model_calls += 1
    _LLM_STATS.total_inference_ms += duration_ms


def llm_run_stats() -> LLMRunStats:
    return _LLM_STATS


def artifacts_from_benchmark(benchmark: GoldBenchmark) -> list[Artifact]:
    return [
        Artifact(
            id=row["id"],
            source=row["source"],
            source_id=row["source_id"],
            type=row["type"],
            author=row.get("author"),
            timestamp=row.get("timestamp"),
            title=row.get("title"),
            content=row["content"],
            metadata=row.get("metadata") or {},
        )
        for row in benchmark.artifacts
    ]


def run_dir(eval_root: Path, run_id: str) -> Path:
    normalized = run_id if run_id.startswith("run_") else f"run_{run_id}"
    return eval_root / normalized


@dataclass
class ExtractionEvalRun:
    run_id: str
    strategy: str
    benchmark: GoldBenchmark
    eval_root: Path = DEFAULT_EVAL_ROOT
    workers: int = 1
    write_predictions: bool = True
    llm_stats: LLMRunStats = field(default_factory=LLMRunStats)

    def _extract_claims(self, artifacts: list[Artifact]) -> list:
        from continuum.extract.schemas import Claim

        if self.strategy == "deterministic" or self.workers <= 1:
            return extract_claims(artifacts, method=self.strategy)

        from concurrent.futures import ThreadPoolExecutor, as_completed

        claims: list[Claim] = []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {
                pool.submit(extract_claims, [artifact], self.strategy): artifact
                for artifact in artifacts
            }
            for future in as_completed(futures):
                try:
                    claims.extend(future.result(timeout=30))
                except Exception:
                    continue
        return claims

    def execute(self) -> dict[str, Any]:
        load_local_env()
        reset_llm_stats()
        tracemalloc.start()
        started = time.perf_counter()

        artifacts = artifacts_from_benchmark(self.benchmark)
        mentions = extract_mentions(artifacts, method=self.strategy)
        claims = self._extract_claims(artifacts)

        runtime_sec = round(time.perf_counter() - started, 3)
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory_peak_mb = round(peak_bytes / (1024 * 1024), 2)
        try:
            if resource is not None:
                rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                if sys.platform == "darwin":
                    rss_mb = rss / (1024 * 1024)
                else:
                    rss_mb = rss / 1024
                memory_peak_mb = round(max(memory_peak_mb, rss_mb), 2)
        except Exception:
            pass

        self.llm_stats = llm_run_stats()
        metrics = {
            "mention": score_gold_mentions(mentions, self.benchmark),
            "claim_strict": score_gold_claims_strict(claims, self.benchmark),
            "claim_abstention": score_gold_claims_abstention(claims, self.benchmark),
            "claim_by_predicate": score_gold_claims_by_predicate(claims, self.benchmark),
            "counts": {
                "artifacts": len(artifacts),
                "mentions_extracted": len(mentions),
                "claims_extracted": len(claims),
            },
        }
        failure_summary, failure_examples = build_failure_corpus(claims, self.benchmark)

        config = {
            "run_id": self.run_id,
            "strategy": self.strategy,
            "dataset_version": self.benchmark.manifest.get("dataset_version"),
            "commit_sha": git_commit_sha(),
            "prompt_version": PROMPT_VERSION,
            "model": llm_model_name() if self.strategy != "deterministic" else None,
            "llm_available": llm_available(),
            "workers": self.workers,
        }

        runtime = {
            "runtime_sec": runtime_sec,
            "memory_peak_mb": memory_peak_mb,
            "model_calls": self.llm_stats.model_calls,
            "avg_inference_ms": self.llm_stats.avg_inference_ms,
            "total_inference_ms": round(self.llm_stats.total_inference_ms, 2),
        }

        out_dir = run_dir(self.eval_root, self.run_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

        report = {
            "run_id": self.run_id,
            "strategy": self.strategy,
            "dataset_version": config["dataset_version"],
            "commit_sha": config["commit_sha"],
            "model": config["model"],
            "prompt_version": PROMPT_VERSION,
            "runtime": runtime,
            "metrics": metrics,
            "failure_summary": failure_summary,
            "failure_example_count": len(failure_examples),
            "system_owner_next_step": _next_step(metrics, failure_summary),
        }
        (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

        if self.write_predictions:
            pred_dir = out_dir / "predictions"
            pred_dir.mkdir(exist_ok=True)
            write_jsonl(pred_dir / "mentions.jsonl", [mention_to_dict(m) for m in mentions])
            write_jsonl(pred_dir / "claims.jsonl", [claim_to_dict(c) for c in claims])

        failures_root = self.eval_root / "failures"
        failures_root.mkdir(parents=True, exist_ok=True)
        _write_failure_slices(failures_root, self.run_id, failure_examples)

        return report


def _next_step(metrics: dict[str, Any], failure_summary: dict[str, int]) -> str:
    strict = metrics.get("claim_strict", {})
    if strict.get("tp", 0) == 0:
        return "Expand VALID gold claim labels and tighten extraction prompts for entity-pair claims."
    top = sorted(failure_summary.items(), key=lambda item: -item[1])[:3]
    if top:
        cats = ", ".join(f"{cat}={count}" for cat, count in top)
        return f"Review failure corpus top categories: {cats}."
    return "Benchmark stable; proceed to scaling-slice experiments."


def _write_failure_slices(root: Path, run_id: str, examples: list[dict[str, Any]]) -> None:
    by_category: dict[str, list[dict[str, Any]]] = {}
    for example in examples:
        by_category.setdefault(example["category"], []).append(example)
    for category, rows in by_category.items():
        path = root / f"{category.lower()}.jsonl"
        existing = []
        if path.exists():
            existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        merged = existing + [{**row, "run_id": run_id} for row in rows[:25]]
        write_jsonl(path, merged)


def run_extraction_eval(
    *,
    run_id: str,
    strategy: str = "deterministic",
    gold_root: Path = DEFAULT_GOLD_ROOT,
    eval_root: Path = DEFAULT_EVAL_ROOT,
    write_predictions: bool = False,
    workers: int = 5,
) -> dict[str, Any]:
    benchmark = load_gold_benchmark(gold_root)
    runner = ExtractionEvalRun(
        run_id=run_id,
        strategy=strategy,
        benchmark=benchmark,
        eval_root=eval_root,
        write_predictions=write_predictions,
        workers=workers if strategy != "deterministic" else 1,
    )
    return runner.execute()
