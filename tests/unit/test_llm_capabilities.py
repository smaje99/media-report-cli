from __future__ import annotations

import pytest

from media_report.core.errors import LLMProviderConfigurationError
from media_report.core.settings import AppSettings
from media_report.infrastructure.llm import (
  OLLAMA_PROVIDER,
  OPENAI_COMPATIBLE_PROVIDER,
  build_llm_provider_resolver,
  get_llm_capability,
  normalize_ollama_base_url,
)


def test_normalize_ollama_base_url_adds_v1_suffix() -> None:
  assert normalize_ollama_base_url("http://localhost:11434") == "http://localhost:11434/v1"
  assert normalize_ollama_base_url("http://localhost:11434/v1") == "http://localhost:11434/v1"


def test_build_llm_provider_resolver_rejects_unknown_provider() -> None:
  resolver = build_llm_provider_resolver(AppSettings())

  with pytest.raises(LLMProviderConfigurationError):
    resolver("unknown-provider")


def test_build_llm_provider_resolver_requires_openai_key() -> None:
  resolver = build_llm_provider_resolver(
    AppSettings(
      llm_provider=OPENAI_COMPATIBLE_PROVIDER,
      openai_api_key=None,
    )
  )

  with pytest.raises(LLMProviderConfigurationError):
    resolver(OPENAI_COMPATIBLE_PROVIDER)


def test_get_llm_capability_reports_remote_provider_ready(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.llm.capabilities.load_pydantic_ai_module",
    lambda: object(),
  )
  settings = AppSettings(
    llm_provider=OPENAI_COMPATIBLE_PROVIDER,
    openai_api_key="sk-example-secret",
    openai_base_url="https://example.invalid/v1",
  )

  capability = get_llm_capability(settings)

  assert capability.provider == OPENAI_COMPATIBLE_PROVIDER
  assert capability.available is True
  assert capability.is_remote is True
  assert capability.warning == "Requests may leave the local machine."


def test_get_llm_capability_reports_local_ollama_ready(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.llm.capabilities.load_pydantic_ai_module",
    lambda: object(),
  )
  monkeypatch.setattr(
    "media_report.infrastructure.llm.capabilities.shutil.which",
    lambda _cmd: "/usr/bin/ollama",
  )
  capability = get_llm_capability(
    AppSettings(
      llm_provider=OLLAMA_PROVIDER,
      ollama_base_url="http://localhost:11434",
    )
  )

  assert capability.provider == OLLAMA_PROVIDER
  assert capability.available is True
  assert capability.is_remote is False
  assert capability.detail.endswith("/v1.")
