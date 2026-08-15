"""Sentence-transformers embedding provider (CPU, swappable)."""

from __future__ import annotations

from .provider import EmbeddingProvider


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device=device)
        self._name = model_name
        dim_fn = getattr(self._model, "get_embedding_dimension", None)
        if dim_fn is None:
            dim_fn = self._model.get_sentence_embedding_dimension
        self._dim = dim_fn()

    @property
    def name(self) -> str:
        return self._name

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()