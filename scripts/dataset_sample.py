"""Build a small deterministic representative sample from the pinned archive.

The sample deliberately includes normal, long, and short records across all nine
sources so Phase 2A can study the shape of reality before building the graph.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import zipfile
from pathlib import Path

from continuum.dataset.artifact import Artifact, artifact_to_dict
from continuum.dataset.download import download_all_documents, open_corpus
from continuum.dataset.manifest import SOURCE_ALIASES

DEFAULT_RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples"
SEED = 20260815


def select_names(archive: zipfile.ZipFile, per_source: int = 40, seed: int = SEED) -> list[str]:
    rng = random.Random(seed)
    names = [n for n in archive.namelist() if not n.endswith("/")]
    selected = []
    for source in sorted(SOURCE_ALIASES):
        prefix = f"{source}/"
        files = [n for n in names if n.startswith(prefix)]
        if not files:
            continue
        sizes = {n: archive.getinfo(n).file_size for n in files}
        small = [n for n in files if sizes[n] < 700]
        large = [n for n in files if sizes[n] > 9000]
        mid = [n for n in files if 700 <= sizes[n] <= 9000]
        buckets = {"short": small, "long": large, "normal": mid}
        picked = []
        per_bucket = max(1, per_source // 3)
        for name in ("short", "long", "normal"):
            bucket = buckets[name]
            picked.extend(rng.sample(bucket, min(per_bucket, len(bucket))))
        while len(picked) < per_source and files:
            candidate = rng.choice(files)
            if candidate not in picked:
                picked.append(candidate)
        selected.extend(picked)
    return selected


def build_sample(archive: zipfile.ZipFile, per_source: int = 40, seed: int = SEED) -> tuple[list[dict], list[dict]]:
    names = select_names(archive, per_source=per_source, seed=seed)
    artifacts = []
    rejected = []
    for name in names:
        source = name.split("/", 1)[0]
        text = archive.read(name).decode("utf-8", errors="replace")
        try:
            artifact = Artifact.from_raw(source=source, path=name, text=text)
            artifacts.append(artifact_to_dict(artifact))
        except ValueError as exc:
            rejected.append({"path": name, "reason": str(exc)})
    return artifacts, rejected


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the Phase 2A representative sample")
    parser.add_argument("--cache", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--per-source", type=int, default=40)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    download_all_documents(args.cache, verify=True)
    with open_corpus(args.cache) as archive:
        artifacts, rejected = build_sample(archive, per_source=args.per_source, seed=args.seed)

    args.out.mkdir(parents=True, exist_ok=True)
    sample_path = args.out / "phase2a-sample.jsonl"
    with sample_path.open("w", encoding="utf-8") as handle:
        for artifact in artifacts:
            handle.write(json.dumps(artifact, ensure_ascii=False) + "\n")

    digest = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    report = {
        "seed": args.seed,
        "per_source": args.per_source,
        "sample_file": str(sample_path),
        "records": len(artifacts),
        "rejected": len(rejected),
        "sha256": digest,
        "rejected_detail": rejected,
        "sources": sorted({a["source"] for a in artifacts}),
    }
    report_path = args.out / "phase2a-sample-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())