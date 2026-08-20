"""Benchmark foundation v1 — manifest, question, and result schemas."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BENCHMARK_VERSION = "v1"
DATASET_NAME = "EnterpriseRAG-Bench"
DATASET_VERSION = "v1.0.0"
MODES = frozenset({"sample-v1", "full-v1", "subset-20pct"})
SYSTEMS = ("bm25", "dense", "hybrid", "continuum")

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RAW = ROOT / "data" / "raw"
DEFAULT_BENCHMARK_ROOT = ROOT / "data" / "evals" / "benchmark-v1"
DEFAULT_SAMPLE_CORPUS = ROOT / "data" / "samples" / "phase2a-sample.jsonl"

DEFAULT_TOP_K = 5
DEFAULT_CONTEXT_CHARS = 12000
DEFAULT_ANSWER_MODEL = "mock-v1"
DEFAULT_REAL_MODEL = "accounts/fireworks/models/gpt-oss-20b"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TIMEOUT_S = 30


def git_commit_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


@dataclass
class BenchmarkManifest:
    benchmark_version: str = BENCHMARK_VERSION
    dataset: str = DATASET_NAME
    dataset_version: str = DATASET_VERSION
    corpus_mode: str = "sample-v1"
    official_benchmark: bool = False
    question_set_version: str = "sample-v1-001"
    question_count: int = 0
    sample_corpus_overlap_count: int = 0
    corpus_path: str = ""
    corpus_record_count: int = 0
    top_k: int = DEFAULT_TOP_K
    context_char_budget: int = DEFAULT_CONTEXT_CHARS
    answer_model: str = DEFAULT_ANSWER_MODEL
    answer_temperature: float = DEFAULT_TEMPERATURE
    answer_timeout_s: int = DEFAULT_TIMEOUT_S
    selection_seed: int = 20260816
    commit_sha: str = field(default_factory=git_commit_sha)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "dataset": self.dataset,
            "dataset_version": self.dataset_version,
            "corpus_mode": self.corpus_mode,
            "official_benchmark": self.official_benchmark,
            "question_set_version": self.question_set_version,
            "question_count": self.question_count,
            "sample_corpus_overlap_count": self.sample_corpus_overlap_count,
            "corpus_path": self.corpus_path,
            "corpus_record_count": self.corpus_record_count,
            "top_k": self.top_k,
            "context_char_budget": self.context_char_budget,
            "answer_model": self.answer_model,
            "answer_temperature": self.answer_temperature,
            "answer_timeout_s": self.answer_timeout_s,
            "selection_seed": self.selection_seed,
            "commit_sha": self.commit_sha,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkManifest":
        return cls(
            benchmark_version=str(data.get("benchmark_version", BENCHMARK_VERSION)),
            dataset=str(data.get("dataset", DATASET_NAME)),
            dataset_version=str(data.get("dataset_version", DATASET_VERSION)),
            corpus_mode=str(data.get("corpus_mode", "sample-v1")),
            official_benchmark=bool(data.get("official_benchmark", False)),
            question_set_version=str(data.get("question_set_version", "")),
            question_count=int(data.get("question_count") or 0),
            sample_corpus_overlap_count=int(data.get("sample_corpus_overlap_count") or 0),
            corpus_path=str(data.get("corpus_path") or ""),
            corpus_record_count=int(data.get("corpus_record_count") or 0),
            top_k=int(data.get("top_k") or DEFAULT_TOP_K),
            context_char_budget=int(data.get("context_char_budget") or DEFAULT_CONTEXT_CHARS),
            answer_model=str(data.get("answer_model") or DEFAULT_ANSWER_MODEL),
            answer_temperature=float(data.get("answer_temperature") or DEFAULT_TEMPERATURE),
            answer_timeout_s=int(data.get("answer_timeout_s") or DEFAULT_TIMEOUT_S),
            selection_seed=int(data.get("selection_seed") or 20260816),
            commit_sha=str(data.get("commit_sha") or git_commit_sha()),
            note=str(data.get("note") or ""),
        )


def mode_root(mode: str, root: Path | None = None) -> Path:
    if mode not in MODES:
        raise ValueError(f"unknown corpus mode: {mode}")
    return (root or DEFAULT_BENCHMARK_ROOT) / mode


def load_manifest(mode: str, root: Path | None = None) -> BenchmarkManifest:
    path = mode_root(mode, root) / "manifest.json"
    return BenchmarkManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_questions(mode: str, root: Path | None = None, *, regression: bool = False) -> list[dict[str, Any]]:
    base = mode_root(mode, root)
    path = base / "regression" / "questions.jsonl" if regression else base / "questions.jsonl"
    return load_questions_from_path(path)


def load_questions_from_path(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_question_ids_from_path(path: Path) -> list[str]:
    """Load question IDs from JSON array or JSONL question rows."""
    if path.suffix == ".jsonl":
        return [str(row["question_id"]) for row in load_questions_from_path(path)]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        if not payload:
            return []
        if isinstance(payload[0], str):
            return [str(item) for item in payload]
        return [str(item["question_id"]) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and "question_ids" in payload:
        return [str(item) for item in payload["question_ids"]]
    raise ValueError(f"unsupported question id file format: {path}")


def filter_questions_by_ids(
    questions: list[dict[str, Any]],
    question_ids: list[str],
) -> list[dict[str, Any]]:
    by_id = {str(q["question_id"]): q for q in questions}
    missing = [qid for qid in question_ids if qid not in by_id]
    if missing:
        raise ValueError(f"unknown question_ids: {missing[:5]}")
    return [by_id[qid] for qid in question_ids]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def validate_question_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("question_id", "question", "question_type", "gold_answer", "expected_doc_ids"):
        if key not in row:
            errors.append(f"missing {key}")
    return errors


def validate_result_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("question_id", "system", "answer", "retrieved_artifacts", "model", "latency_ms"):
        if key not in row:
            errors.append(f"missing {key}")
    breakdown = row.get("latency_breakdown")
    if not isinstance(breakdown, dict):
        errors.append("latency_breakdown must be an object")
    return errors
