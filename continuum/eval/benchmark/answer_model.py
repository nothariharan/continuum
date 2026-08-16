"""Shared real answer model for all benchmark systems."""

from __future__ import annotations

from dataclasses import dataclass

from continuum.extract.llm_client import create_llm_client, llm_config_from_env, load_local_env

from .answer_mock import ANSWER_PROMPT, estimate_tokens


@dataclass
class RealAnswerModel:
    temperature: float = 0.0
    timeout_s: int = 30

    def __post_init__(self) -> None:
        load_local_env()
        self._config = llm_config_from_env()
        if self._config is None:
            raise RuntimeError(
                "Real answer model requires FIREWORKS_API_KEY or OPENAI_API_KEY in the environment"
            )
        self._client = create_llm_client()

    @property
    def name(self) -> str:
        return self._config.model if self._config else "unknown"

    def generate(self, question: str, context: str) -> tuple[str, int, float]:
        import time

        prompt = ANSWER_PROMPT.format(question=question, context=context)
        started = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=512,
        )
        generation_ms = (time.perf_counter() - started) * 1000
        answer = (response.choices[0].message.content or "").strip()
        return answer, estimate_tokens(answer), generation_ms
