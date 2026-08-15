"""Fireworks / OpenAI-compatible client configuration for LLM extraction."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
DEFAULT_FIREWORKS_MODEL = "accounts/fireworks/models/gpt-oss-20b"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str
    base_url: str | None
    model: str

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


def load_local_env(env_path: Path | None = None) -> None:
    """Load workspace .env without overriding existing environment variables."""
    if env_path is None:
        env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def llm_config_from_env() -> LLMConfig | None:
    """Prefer Fireworks when FIREWORKS_API_KEY is set; else OpenAI."""
    fireworks_key = os.environ.get("FIREWORKS_API_KEY", "").strip()
    if fireworks_key:
        model = os.environ.get("CONTINUUM_LLM_MODEL", DEFAULT_FIREWORKS_MODEL)
        return LLMConfig(
            provider="fireworks",
            api_key=fireworks_key,
            base_url=os.environ.get("CONTINUUM_LLM_BASE_URL", FIREWORKS_BASE_URL),
            model=model,
        )
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        return LLMConfig(
            provider="openai",
            api_key=openai_key,
            base_url=os.environ.get("CONTINUUM_LLM_BASE_URL") or None,
            model=os.environ.get("CONTINUUM_LLM_MODEL", DEFAULT_OPENAI_MODEL),
        )
    return None


def llm_available() -> bool:
    config = llm_config_from_env()
    return config is not None and config.enabled


def create_llm_client():
    """Return an OpenAI SDK client configured for Fireworks or OpenAI."""
    from openai import OpenAI

    config = llm_config_from_env()
    if config is None:
        raise RuntimeError(
            "LLM extraction requires FIREWORKS_API_KEY or OPENAI_API_KEY in the environment"
        )
    if config.base_url:
        return OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=20.0, max_retries=1)
    return OpenAI(api_key=config.api_key, timeout=20.0, max_retries=1)


def llm_model_name() -> str:
    config = llm_config_from_env()
    return config.model if config else DEFAULT_FIREWORKS_MODEL


def parse_json_array(content: str) -> list:
    """Parse a JSON array from raw LLM output, tolerating markdown fences."""
    text = (content or "").strip()
    if not text:
        return []
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    payload = json.loads(text)
    return payload if isinstance(payload, list) else []
