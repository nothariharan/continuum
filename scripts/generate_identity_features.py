#!/usr/bin/env python3
"""Attach FeatureVector-compatible features to identity-pair rows."""

from __future__ import annotations

import argparse
from pathlib import Path

from continuum.eval.identity.features import attach_features, load_artifact_index
from continuum.eval.identity.schema import DEFAULT_DATASET_PATH, load_identity_pairs, write_identity_pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Compute embedding_similarity via sentence-transformers (optional)",
    )
    args = parser.parse_args()

    rows = load_identity_pairs(args.input)
    provider = None
    if args.embed:
        try:
            from continuum.embed.sentence_transformer import SentenceTransformerProvider

            provider = SentenceTransformerProvider()
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise SystemExit(f"--embed requested but embedding provider unavailable: {exc}") from exc

    index = load_artifact_index()
    enriched = attach_features(rows, index=index, embedding_provider=provider)
    write_identity_pairs(enriched, args.output)
    print(f"attached features to {len(enriched)} pairs -> {args.output}")


if __name__ == "__main__":
    main()
