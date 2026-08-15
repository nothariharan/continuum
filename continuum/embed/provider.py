"""Embedding provider interface so the model can be swapped later."""

from __future__ import annotations

import abc


class EmbeddingProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError