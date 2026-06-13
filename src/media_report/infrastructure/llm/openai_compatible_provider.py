from __future__ import annotations

import importlib
from typing import Any

from media_report.core.errors import (
  LLMProviderConfigurationError,
  LLMProviderExecutionError,
  LLMProviderOutputError,
)
from media_report.core.redaction import redact_text
from media_report.domain.reporting.ports import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
  def __init__(self, *, api_key: str | None, base_url: str) -> None:
    if not api_key:
      raise LLMProviderConfigurationError(
        "OpenAI-compatible provider requires MEDIA_REPORT_OPENAI_API_KEY."
      )
    self._api_key = api_key
    self._base_url = base_url

  def generate(self, prompt: str, *, model: str) -> str:
    try:
      return _run_openai_compatible_prompt(
        prompt=prompt,
        model=model,
        api_key=self._api_key,
        base_url=self._base_url,
      )
    except LLMProviderOutputError:
      raise
    except Exception as exc:  # pragma: no cover - exercised by tests via patching.
      raise LLMProviderExecutionError(
        redact_text(
          f"OpenAI-compatible provider failed for model '{model}': {exc}",
          secrets=(self._api_key,),
        )
      ) from exc


def _run_openai_compatible_prompt(
  *,
  prompt: str,
  model: str,
  api_key: str,
  base_url: str,
) -> str:
  try:
    agent_module = importlib.import_module("pydantic_ai")
    model_module = importlib.import_module("pydantic_ai.models.openai")
    provider_module = importlib.import_module("pydantic_ai.providers.openai")
  except ImportError as exc:  # pragma: no cover - handled by doctor/capability checks.
    raise LLMProviderExecutionError("Pydantic AI runtime is not available.") from exc

  provider = provider_module.OpenAIProvider(base_url=base_url, api_key=api_key)
  agent = agent_module.Agent(
    model=model_module.OpenAIChatModel(model, provider=provider),
    output_type=str,
  )
  result = agent.run_sync(prompt)
  output = _extract_output(result)
  if not output.strip():
    raise LLMProviderOutputError("OpenAI-compatible provider returned empty output.")
  return output


def _extract_output(result: Any) -> str:
  output = getattr(result, "output", None)
  if isinstance(output, str):
    return output
  if output is None:
    raise LLMProviderOutputError("LLM result did not expose textual output.")
  return str(output)
