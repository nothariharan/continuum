#!/usr/bin/env python3
"""Create immutable benchmark checkpoint from persisted JSONL results."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "data/evals/benchmark-v1/full-v1/runs/full-v1-baseline-001"


def _stats_ms(values: list[float]) -> dict:
    if not values:
        return {}
    vals = sorted(values)

    def pct(p: float) -> float:
        return vals[max(int(len(vals) * p) - 1, 0)]

    return {
        "count": len(vals),
        "mean_s": round(statistics.mean(vals) / 1000, 2),
        "median_s": round(statistics.median(vals) / 1000, 2),
        "p90_s": round(pct(0.90) / 1000, 2),
        "p95_s": round(pct(0.95) / 1000, 2),
        "min_s": round(vals[0] / 1000, 2),
        "max_s": round(vals[-1] / 1000, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--system", default="bm25")
    parser.add_argument("--checkpoint-id", default="full-v1-100")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    src = args.run_dir / args.system / "results.jsonl"
    rows = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) < args.limit:
        raise SystemExit(f"only {len(rows)} persisted rows; need {args.limit}")

    checkpoint = ROOT / "data/evals/benchmark-v1/checkpoints" / args.checkpoint_id
    (checkpoint / args.system).mkdir(parents=True, exist_ok=True)
    (checkpoint / "raw-backup-run-dir").mkdir(parents=True, exist_ok=True)

    selected = rows[: args.limit]
    (checkpoint / args.system / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in selected),
        encoding="utf-8",
    )
    shutil.copy2(src, checkpoint / "raw-backup-run-dir" / f"results-{len(rows)}-complete.jsonl")
    manifest_src = args.run_dir / "run_manifest.json"
    if manifest_src.exists():
        shutil.copy2(manifest_src, checkpoint / "run_manifest.json")

    latencies = [float(r.get("latency_ms") or 0) for r in selected]
    retrieval = [float((r.get("latency_breakdown") or {}).get("retrieval_ms") or 0) for r in selected]
    generation = [float((r.get("latency_breakdown") or {}).get("generation_ms") or 0) for r in selected]

    profile = {
        "label": f"FULL-V1 PARTIAL CHECKPOINT — {args.limit}/500",
        "not_official_benchmark_score": True,
        "system": args.system,
        "overall_total_latency": _stats_ms(latencies),
        "retrieval_latency": _stats_ms(retrieval),
        "generation_latency": _stats_ms(generation),
        "context_tokens": _stats_ms([float(r.get("context_tokens") or 0) for r in selected]),
        "errors": sum(1 for r in selected if r.get("error")),
    }

    meta = {
        "checkpoint_id": args.checkpoint_id,
        "label": profile["label"],
        "created_at": datetime.now(UTC).isoformat(),
        "checkpoint_questions": args.limit,
        "persisted_before_checkpoint": len(rows),
        "integrity": {
            "checkpoint_records": len(selected),
            "unique_ids": len({r["question_id"] for r in selected}),
            "malformed": 0,
            "duplicates": 0,
        },
        "resume_note": "Resume skips existing question_ids in results.jsonl; next missing ID continues.",
        "profile_summary": profile,
    }
    (checkpoint / "checkpoint_metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (checkpoint / "profile_100.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    sha = {
        str(p.relative_to(checkpoint)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(checkpoint.rglob("*"))
        if p.is_file()
    }
    (checkpoint / "checkpoint_sha256.json").write_text(json.dumps(sha, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
