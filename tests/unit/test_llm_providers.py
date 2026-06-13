from __future__ import annotations

import pytest

from media_report.core.errors import (
  LLMProviderConfigurationError,
  LLMProviderExecutionError,
  LLMProviderOutputError,
)
from media_report.infrastructure.llm import OllamaProvider, OpenAICompatibleProvider


def test_ollama_provider_returns_markdown_without_real_network(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.llm.ollama_provider._run_ollama_prompt",
    lambda **_: "# Report\n\n- item",
  )

  result = OllamaProvider(base_url="http://localhost:11434/v1").generate(
    "Prompt",
    model="llama3.1",
  )

  assert result == "# Report\n\n- item"


def test_ollama_provider_preserves_output_validation(monkeypatch) -> None:
  def fake_run(**_kwargs: object) -> str:
    raise LLMProviderOutputError("Ollama provider returned empty output.")

  monkeypatch.setattr(
    "media_report.infrastructure.llm.ollama_provider._run_ollama_prompt",
    fake_run,
  )

  with pytest.raises(LLMProviderOutputError):
    OllamaProvider(base_url="http://localhost:11434/v1").generate("Prompt", model="llama3.1")


def test_openai_compatible_provider_requires_api_key() -> None:
  with pytest.raises(LLMProviderConfigurationError):
    OpenAICompatibleProvider(api_key=None, base_url="https://example.invalid/v1")


def test_openai_compatible_provider_returns_markdown_without_real_network(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.llm.openai_compatible_provider._run_openai_compatible_prompt",
    lambda **_: "# Remote Report",
  )

  result = OpenAICompatibleProvider(
    api_key="sk-example-secret",
    base_url="https://example.invalid/v1",
  ).generate("Prompt", model="gpt-4.1-mini")

  assert result == "# Remote Report"


def test_openai_compatible_provider_redacts_api_keys_in_errors(monkeypatch) -> None:
  def fake_run(**_kwargs: object) -> str:
    raise RuntimeError("Bearer sk-example-secret request failed")

  monkeypatch.setattr(
    "media_report.infrastructure.llm.openai_compatible_provider._run_openai_compatible_prompt",
    fake_run,
  )

  provider = OpenAICompatibleProvider(
    api_key="sk-example-secret",
    base_url="https://example.invalid/v1",
  )

  with pytest.raises(LLMProviderExecutionError) as exc_info:
    provider.generate("Prompt", model="gpt-4.1-mini")

  message = str(exc_info.value)
  assert "sk-example-secret" not in message
  assert "Bearer ***" in message
