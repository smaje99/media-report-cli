from __future__ import annotations

import importlib
import shutil
from collections.abc import Callable
from types import ModuleType
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict

from media_report.core.errors import (
  LLMProviderConfigurationError,
  OptionalDependencyMissingError,
)
from media_report.core.settings import AppSettings
from media_report.domain.reporting.ports import LLMProvider
from media_report.infrastructure.llm.ollama_provider import OllamaProvider
from media_report.infrastructure.llm.openai_compatible_provider import OpenAICompatibleProvider

LLM_RUNTIME_DEPENDENCY = "pydantic-ai-slim[openai]"
LLM_RUNTIME_INSTALL_HINT = '`pip install "pydantic-ai-slim[openai]"` or `uv sync --extra dev`.'
OLLAMA_PROVIDER = "ollama"
OPENAI_COMPATIBLE_PROVIDER = "openai-compatible"
SUPPORTED_LLM_PROVIDERS = (OLLAMA_PROVIDER, OPENAI_COMPATIBLE_PROVIDER)


class LLMCapability(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  provider: str
  available: bool
  detail: str
  is_remote: bool
  warning: str | None = None
  install_hint: str | None = None


def load_pydantic_ai_module() -> ModuleType:
  try:
    return importlib.import_module("pydantic_ai")
  except ImportError as exc:
    raise OptionalDependencyMissingError(
      dependency_name=LLM_RUNTIME_DEPENDENCY,
      feature_name="LLM report generation",
      install_hint=LLM_RUNTIME_INSTALL_HINT,
    ) from exc


def normalize_ollama_base_url(base_url: str) -> str:
  normalized = base_url.rstrip("/")
  return normalized if normalized.endswith("/v1") else f"{normalized}/v1"


def validate_base_url(base_url: str, *, field_name: str) -> str:
  candidate = base_url.strip()
  parts = urlsplit(candidate)
  if parts.scheme not in {"http", "https"} or not parts.netloc:
    raise LLMProviderConfigurationError(
      f"Invalid {field_name}: '{base_url}'. Use a full http(s) URL."
    )
  return candidate


def build_llm_provider_resolver(settings: AppSettings) -> Callable[[str], LLMProvider]:
  def resolve(provider_name: str) -> LLMProvider:
    if provider_name == OLLAMA_PROVIDER:
      base_url = normalize_ollama_base_url(
        validate_base_url(settings.ollama_base_url, field_name="ollama base URL")
      )
      return OllamaProvider(base_url=base_url)
    if provider_name == OPENAI_COMPATIBLE_PROVIDER:
      if not settings.openai_api_key:
        raise LLMProviderConfigurationError(
          "OpenAI-compatible provider requires MEDIA_REPORT_OPENAI_API_KEY."
        )
      base_url = validate_base_url(
        settings.openai_base_url,
        field_name="openai-compatible base URL",
      )
      return OpenAICompatibleProvider(
        api_key=settings.openai_api_key,
        base_url=base_url,
      )
    raise LLMProviderConfigurationError(
      "Unknown LLM provider "
      f"'{provider_name}'. Supported providers: {', '.join(SUPPORTED_LLM_PROVIDERS)}."
    )

  return resolve


def get_llm_capability(settings: AppSettings) -> LLMCapability:
  provider_name = settings.llm_provider
  try:
    load_pydantic_ai_module()
  except OptionalDependencyMissingError as exc:
    return LLMCapability(
      provider=provider_name,
      available=False,
      detail=str(exc),
      is_remote=provider_name != OLLAMA_PROVIDER,
      install_hint=LLM_RUNTIME_INSTALL_HINT,
    )

  if provider_name == OLLAMA_PROVIDER:
    try:
      base_url = normalize_ollama_base_url(
        validate_base_url(settings.ollama_base_url, field_name="ollama base URL")
      )
    except LLMProviderConfigurationError as exc:
      return LLMCapability(
        provider=provider_name,
        available=False,
        detail=str(exc),
        is_remote=False,
      )
    if shutil.which("ollama") is None:
      return LLMCapability(
        provider=provider_name,
        available=False,
        detail="Ollama command not found in PATH.",
        is_remote=False,
      )

    return LLMCapability(
      provider=provider_name,
      available=True,
      detail=f"Configured for local Ollama at {base_url}.",
      is_remote=False,
    )

  if provider_name == OPENAI_COMPATIBLE_PROVIDER:
    try:
      validate_base_url(settings.openai_base_url, field_name="openai-compatible base URL")
    except LLMProviderConfigurationError as exc:
      return LLMCapability(
        provider=provider_name,
        available=False,
        detail=str(exc),
        is_remote=True,
      )
    if not settings.openai_api_key:
      return LLMCapability(
        provider=provider_name,
        available=False,
        detail="OpenAI-compatible provider requires MEDIA_REPORT_OPENAI_API_KEY.",
        is_remote=True,
      )
    return LLMCapability(
      provider=provider_name,
      available=True,
      detail="Remote provider configured.",
      is_remote=True,
      warning="Requests may leave the local machine.",
    )

  return LLMCapability(
    provider=provider_name,
    available=False,
    detail=(
      "Unknown LLM provider "
      f"'{provider_name}'. Supported providers: {', '.join(SUPPORTED_LLM_PROVIDERS)}."
    ),
    is_remote=True,
    warning="Unknown provider will not be usable for report generation.",
  )
