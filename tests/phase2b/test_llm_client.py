"""LLM client configuration tests."""

import json

from continuum.extract.llm_client import (
    DEFAULT_FIREWORKS_MODEL,
    llm_config_from_env,
    llm_available,
    parse_json_array,
)


def test_fireworks_config_preferred(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw_test_key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = llm_config_from_env()
    assert config is not None
    assert config.provider == "fireworks"
    assert config.model == DEFAULT_FIREWORKS_MODEL
    assert llm_available()


def test_openai_fallback(monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    config = llm_config_from_env()
    assert config is not None
    assert config.provider == "openai"


def test_parse_json_array_with_fence():
    payload = parse_json_array('```json\n[{"raw_text": "Sarah Chen"}]\n```')
    assert payload == [{"raw_text": "Sarah Chen"}]


def test_parse_json_array_plain():
    payload = parse_json_array(json.dumps([{"predicate": "OWNS"}]))
    assert payload[0]["predicate"] == "OWNS"
