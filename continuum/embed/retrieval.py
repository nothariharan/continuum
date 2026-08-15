"""Dense + hybrid retrievers over an embedding provider."""

from __future__ import annotations

import numpy as np

from .bm25 import BM25Retriever
from .provider import EmbeddingProvider


class DenseRetriever:
    def __init__(self, provider: EmbeddingProvider, corpus: list[str]) -> None:
        self.provider = provider
        self._corpus = corpus
        vectors = np.asarray(provider.embed(corpus), dtype=np.float32)
        self._matrix = vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        q = np.asarray(self.provider.embed([query]), dtype=np.float32)
        q = q / np.maximum(np.linalg.norm(q), 1e-12)
        scores = self._matrix @ q.T
        order = np.argsort(scores.ravel())[::-1][:top_k]
        return [(int(i), float(scores[i, 0])) for i in order]


class HybridRetriever:
    """Reciprocal-rank fusion of BM25 and dense scores."""

    def __init__(self, provider: EmbeddingProvider, corpus: list[str], dense_weight: float = 1.0) -> None:
        self._bm25 = BM25Retriever(corpus)
        self._dense = DenseRetriever(provider, corpus)
        self._dense_weight = dense_weight

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        pool = 50
        bm25_hits = self._bm25.search(query, top_k=pool)
        dense_hits = self._dense.search(query, top_k=pool)
        scores: dict[int, float] = {}
        for rank, (i, _) in enumerate(bm25_hits):
            scores[i] = scores.get(i, 0.0) + 1.0 / (60 + rank)
        for rank, (i, _) in enumerate(dense_hits):
            scores[i] = scores.get(i, 0.0) + self._dense_weight / (60 + rank)
        order = sorted(scores, key=scores.get, reverse=True)
        return [(i, scores[i]) for i in order[:top_k]]