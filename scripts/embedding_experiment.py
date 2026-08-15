"""Embedding + retrieval experiment on the Phase 2A sample.

Compares BM25 (lexical) vs semantic dense vs hybrid (RRF) on a small
manually-defined query/relevance set. Reports Recall@5/@10, indexing time,
query latency, model name, embedding dimension, and corpus size.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from continuum.embed.bm25 import BM25Retriever
from continuum.embed.retrieval import DenseRetriever, HybridRetriever
from continuum.embed.sentence_transformer import SentenceTransformerProvider

DEFAULT_SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "metadata" / "embedding_experiment.json"

QUERIES = [
    {"q": "Which team owns the deployment-mode assay for hosted, dedicated, and private?", "relevant": ["MAP: deployment-mode assay & regional close cadence"]},
    {"q": "What billing complaint did QuantaLedger raise about usage and processing regions?", "relevant": ["QuantaLedger exception memo outline"]},
    {"q": "How should the TypeScript SDK cancel an in-flight streaming chat request?", "relevant": ["TypeScript SDK: request abort/cancel support for streaming chat"]},
    {"q": "Which PR added a hierarchical latency fingerprint canary detector?", "relevant": ["add hierarchical latency-fingerprint canary and golden-path gating"]},
    {"q": "What ticket covers removing legacy feature flags in the serving runtime?", "relevant": ["cleanup-unused-feature-flags-in-serving-runtime"]},
    {"q": "What did Redwood promise to explain about attempt-level billing and retries?", "relevant": ["Northwind AI - usage discrepancy escalation sync"]},
    {"q": "Which Slack thread polled about debugging-style cereals?", "relevant": ["1779505555-cereal-debug-styles"]},
    {"q": "What files are attached to the SIG access-orchestration follow-up?", "relevant": ["SIG follow-up: access orchestration"]},
]


def recall_at(ranking: list[tuple[int, float]], relevant_idx: set[int], k: int) -> float:
    top = {i for i, _ in ranking[:k]}
    if not relevant_idx:
        return 0.0
    return len(top & relevant_idx) / len(relevant_idx)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2A retrieval experiment")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--corpus-cap", type=int, default=0, help="limit corpus (0 = all sample)")
    args = parser.parse_args()

    records = []
    with (args.sample / "phase2a-sample.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    corpus_texts = [f"{r['title']}\n{r['content']}" for r in records]
    if args.corpus_cap:
        corpus_texts = corpus_texts[: args.corpus_cap]

    provider = SentenceTransformerProvider(args.model, device=args.device)

    idx_t0 = time.perf_counter()
    bm25 = BM25Retriever(corpus_texts)
    bm25_index_s = time.perf_counter() - idx_t0

    idx_t0 = time.perf_counter()
    dense = DenseRetriever(provider, corpus_texts)
    dense_index_s = time.perf_counter() - idx_t0

    hybrid = HybridRetriever(provider, corpus_texts)

    relevant = []
    for spec in QUERIES:
        matches = [
            i for i, r in enumerate(records) if any(k in (r["title"] or "") for k in spec["relevant"])
        ]
        relevant.append(set(matches))

    results = {"bm25": [], "dense": [], "hybrid": []}
    for query, rel in zip(QUERIES, relevant):
        for name, retriever in (("bm25", bm25), ("dense", dense), ("hybrid", hybrid)):
            t0 = time.perf_counter()
            ranking = retriever.search(query["q"], top_k=10)
            latency = (time.perf_counter() - t0) * 1000
            results[name].append(
                {
                    "query": query["q"],
                    "relevant_count": len(rel),
                    "recall@5": recall_at(ranking, rel, 5),
                    "recall@10": recall_at(ranking, rel, 10),
                    "latency_ms": round(latency, 2),
                }
            )

    def summarize(name: str) -> dict:
        rows = results[name]
        return {
            "mean_recall@5": round(float(np.mean([r["recall@5"] for r in rows])), 4),
            "mean_recall@10": round(float(np.mean([r["recall@10"] for r in rows])), 4),
            "median_latency_ms": round(float(np.median([r["latency_ms"] for r in rows])), 2),
            "per_query": rows,
        }

    payload = {
        "model": provider.name,
        "embedding_dimension": provider.dimension,
        "corpus_size": len(corpus_texts),
        "num_queries": len(QUERIES),
        "bm25_index_s": round(bm25_index_s, 3),
        "dense_index_s": round(dense_index_s, 3),
        "bm25": summarize("bm25"),
        "dense": summarize("dense"),
        "hybrid": summarize("hybrid"),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())