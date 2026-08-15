"""Extract claims from normalized artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from continuum.extract.claim import claims_to_jsonl_rows, extract_claims
from continuum.extract.llm_client import load_local_env
from continuum.extract.schemas import (
    Claim,
    artifacts_from_dicts,
    claim_from_dict,
    load_artifacts_jsonl,
    read_jsonl,
    write_jsonl,
)

DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "phase2a-sample.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "extraction" / "claims.jsonl"


def main() -> int:
    load_local_env()
    parser = argparse.ArgumentParser(description="Extract claims from artifact sample")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--method", choices=["deterministic", "llm", "hybrid"], default="deterministic")
    parser.add_argument("--min-confidence", type=float, default=0.70)
    parser.add_argument("--limit", type=int, default=0, help="limit output rows (0 = all)")
    parser.add_argument("--workers", type=int, default=1, help="parallel workers for llm/hybrid")
    parser.add_argument("--checkpoint", type=Path, default=None, help="write partial JSONL every 50 artifacts")
    args = parser.parse_args()

    rows = load_artifacts_jsonl(args.sample)
    artifacts = artifacts_from_dicts(rows)
    claims: list[Claim] = []
    if args.checkpoint and args.checkpoint.exists():
        claims = [claim_from_dict(row) for row in read_jsonl(args.checkpoint)]
        done_ids = {claim.artifact_id for claim in claims}
        artifacts = [artifact for artifact in artifacts if artifact.id not in done_ids]
        if claims:
            print(
                f"resumed from checkpoint with {len(claims)} claims; {len(artifacts)} artifacts remaining",
                file=sys.stderr,
                flush=True,
            )

    total = len(artifacts)

    def _extract(artifact):
        return extract_claims([artifact], method=args.method)

    if args.method != "deterministic" and args.workers > 1:
        completed = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(_extract, artifact): artifact for artifact in artifacts}
            for future in as_completed(futures):
                try:
                    claims.extend(future.result(timeout=30))
                except Exception as exc:
                    artifact = futures[future]
                    print(
                        f"warning: skipped {artifact.id} after extract failure: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )
                completed += 1
                if completed % 10 == 0 or completed == total:
                    print(
                        f"progress: {completed}/{total} artifacts, {len(claims)} claims so far",
                        file=sys.stderr,
                        flush=True,
                    )
                if args.checkpoint and completed % 50 == 0:
                    filtered = [c for c in claims if c.confidence >= args.min_confidence]
                    write_jsonl(args.checkpoint, claims_to_jsonl_rows(filtered))
    else:
        for index, artifact in enumerate(artifacts, start=1):
            claims.extend(_extract(artifact))
            if args.method != "deterministic" and (index % 10 == 0 or index == total):
                print(
                    f"progress: {index}/{total} artifacts, {len(claims)} claims so far",
                    file=sys.stderr,
                    flush=True,
                )
            if args.checkpoint and index % 50 == 0:
                filtered = [c for c in claims if c.confidence >= args.min_confidence]
                write_jsonl(args.checkpoint, claims_to_jsonl_rows(filtered))
    claims = [c for c in claims if c.confidence >= args.min_confidence]
    claims.sort(key=lambda c: (-c.confidence, c.artifact_id, c.predicate))
    if args.limit:
        claims = claims[: args.limit]
    count = write_jsonl(args.out, claims_to_jsonl_rows(claims))
    print(json.dumps({"claims": count, "artifacts": len(artifacts), "method": args.method, "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
