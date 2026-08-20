"""Build benchmark-v1 manifests and question sets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from continuum.eval.benchmark.corpus import load_corpus, load_sample_corpus
from continuum.eval.benchmark.questions import load_official_questions, sample_corpus_overlap
from continuum.eval.benchmark.schema import (
    DEFAULT_BENCHMARK_ROOT,
    BenchmarkManifest,
    mode_root,
    write_json,
    write_jsonl,
)
from continuum.eval.benchmark.select import (
    DEFAULT_DEV_SIZE,
    DEFAULT_SUBSET_SEED,
    DEFAULT_SUBSET_SIZE,
    category_counts,
    select_dev_holdout_split,
    select_full_v1,
    select_proportional_subset,
    select_regression,
    select_sample_v1,
)

ROOT = Path(__file__).resolve().parents[3]
INVENTORY = ROOT / "data" / "metadata" / "dataset_inventory.json"


def _full_corpus_record_count() -> int:
    if INVENTORY.exists():
        return int(json.loads(INVENTORY.read_text(encoding="utf-8")).get("total_files", 0))
    return 0


def _questions_sha256(question_ids: list[str]) -> str:
    payload = "\n".join(sorted(question_ids)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_subset_20pct(
    *,
    root: Path,
    seed: int,
    target: int,
    dev_size: int,
) -> BenchmarkManifest:
    official = load_official_questions()
    selected = select_proportional_subset(official, target=target, seed=seed)
    question_ids = [str(q["question_id"]) for q in selected]
    dev_ids, holdout_ids = select_dev_holdout_split(question_ids, dev_size=dev_size, seed=seed)
    sample_ids = load_sample_corpus().id_set
    overlap_count = sum(1 for q in selected if sample_corpus_overlap(q, sample_ids))

    out_root = mode_root("subset-20pct", root)
    samples_root = out_root / "samples"
    manifest_payload = {
        "benchmark_version": "v1",
        "mode": "subset-20pct",
        "selection_seed": seed,
        "target_size": target,
        "dev_size": dev_size,
        "holdout_size": len(holdout_ids),
        "question_count": len(selected),
        "question_ids_sha256": _questions_sha256(question_ids),
        "category_counts": category_counts(selected),
        "dev_category_counts": category_counts([q for q in selected if str(q["question_id"]) in set(dev_ids)]),
        "holdout_category_counts": category_counts(
            [q for q in selected if str(q["question_id"]) in set(holdout_ids)]
        ),
        "sample_corpus_overlap_count": overlap_count,
        "note": (
            "Deterministic proportional 20% subset of official 500Q. "
            "Use sample_dev.json for tuning; sample_holdout.json for validation only."
        ),
    }

    write_jsonl(out_root / "questions.jsonl", selected)
    write_json(out_root / "manifest.json", manifest_payload)
    write_json(samples_root / "sample_dev.json", dev_ids)
    write_json(samples_root / "sample_holdout.json", holdout_ids)
    write_json(
        samples_root / "sample_manifest.json",
        {
            "selection_seed": seed,
            "dev_ids": dev_ids,
            "holdout_ids": holdout_ids,
            "question_ids_sha256": manifest_payload["question_ids_sha256"],
        },
    )

    regression = select_regression(selected, limit=10, seed=seed)
    write_jsonl(out_root / "regression" / "questions.jsonl", regression)

    return BenchmarkManifest(
        corpus_mode="subset-20pct",
        official_benchmark=False,
        question_set_version="subset-20pct-001",
        question_count=len(selected),
        sample_corpus_overlap_count=overlap_count,
        corpus_path="data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip",
        corpus_record_count=_full_corpus_record_count(),
        selection_seed=seed,
        note=str(manifest_payload["note"]),
    )


def build_mode(mode: str, *, root: Path, seed: int, sample_target: int) -> BenchmarkManifest:
    if mode == "subset-20pct":
        dev_size = int(os.getenv("BENCHMARK_DEV_SIZE", DEFAULT_DEV_SIZE))
        target = int(os.getenv("BENCHMARK_SAMPLE_SIZE", DEFAULT_SUBSET_SIZE))
        subset_seed = int(os.getenv("BENCHMARK_SAMPLE_SEED", DEFAULT_SUBSET_SEED))
        return build_subset_20pct(root=root, seed=subset_seed, target=target, dev_size=dev_size)

    official = load_official_questions()
    sample_ids = load_sample_corpus().id_set
    overlap_count = sum(1 for q in official if sample_corpus_overlap(q, sample_ids))

    if mode == "full-v1":
        selected = select_full_v1(official)
        corpus_count = _full_corpus_record_count()
        manifest = BenchmarkManifest(
            corpus_mode="full-v1",
            official_benchmark=True,
            question_set_version="full-v1-001",
            question_count=len(selected),
            sample_corpus_overlap_count=overlap_count,
            corpus_path="data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip",
            corpus_record_count=corpus_count,
            selection_seed=seed,
            note="Official benchmark mode: full EnterpriseRAG question coverage on full corpus.",
        )
    elif mode == "sample-v1":
        selected = select_sample_v1(official, target=sample_target, seed=seed)
        corpus = load_corpus("sample-v1")
        manifest = BenchmarkManifest(
            corpus_mode="sample-v1",
            official_benchmark=False,
            question_set_version="sample-v1-001",
            question_count=len(selected),
            sample_corpus_overlap_count=sum(1 for q in selected if sample_corpus_overlap(q, sample_ids)),
            corpus_path="data/samples/phase2a-sample.jsonl",
            corpus_record_count=len(corpus.records),
            selection_seed=seed,
            note=(
                "Development/regression mode only — NOT publishable as official benchmark. "
                f"Only {overlap_count} official questions have gold docs in the 360-doc sample."
            ),
        )
    else:
        raise ValueError(f"unknown mode: {mode}")

    out_root = mode_root(mode, root)
    write_jsonl(out_root / "questions.jsonl", selected)
    write_json(out_root / "manifest.json", manifest.to_dict())

    if mode in ("sample-v1", "full-v1"):
        pool = selected if mode == "sample-v1" else official
        regression = select_regression(pool, limit=10, seed=seed)
        write_jsonl(out_root / "regression" / "questions.jsonl", regression)

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["sample-v1", "full-v1", "subset-20pct", "all"],
        default="all",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--sample-target", type=int, default=75)
    args = parser.parse_args()

    modes = ["sample-v1", "full-v1", "subset-20pct"] if args.mode == "all" else [args.mode]
    for mode in modes:
        manifest = build_mode(mode, root=args.root, seed=args.seed, sample_target=args.sample_target)
        print(
            f"built {mode}: {manifest.question_count} questions -> "
            f"{mode_root(mode, args.root) / 'questions.jsonl'}"
        )


if __name__ == "__main__":
    main()
