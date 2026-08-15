"""BM25 lexical retriever using rank-bm25."""

from __future__ import annotations

import math
import re

from rank_bm25 import BM25Okapi

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


class BM25Retriever:
    def __init__(self, corpus: list[str]) -> None:
        self._bm25 = BM25Okapi([tokenize(doc) for doc in corpus])

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        scores = self._bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [(i, scores[i]) for i in order[:top_k]]