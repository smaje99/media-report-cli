from __future__ import annotations

import importlib
from typing import Any

from media_report.core.errors import LLMProviderExecutionError, LLMProviderOutputError
from media_report.core.redaction import redact_text
from media_report.domain.reporting.ports import LLMProvider


class OllamaProvider(LLMProvider):
  def __init__(self, *, base_url: str) -> None:
    self._base_url = base_url

  def generate(self, prompt: str, *, model: str) -> str:
    try:
      return _run_ollama_prompt(prompt=prompt, model=model, base_url=self._base_url)
    except LLMProviderOutputError:
      raise
    except Exception as exc:  # pragma: no cover - exercised by tests via patching.
      raise LLMProviderExecutionError(
        redact_text(f"Ollama provider failed for model '{model}': {exc}")
      ) from exc


def _run_ollama_prompt(*, prompt: str, model: str, base_url: str) -> str:
  try:
    agent_module = importlib.import_module("pydantic_ai")
    model_module = importlib.import_module("pydantic_ai.models.ollama")
    provider_module = importlib.import_module("pydantic_ai.providers.ollama")
  except ImportError as exc:  # pragma: no cover - handled by doctor/capability checks.
    raise LLMProviderExecutionError("Pydantic AI runtime is not available.") from exc

  provider = provider_module.OllamaProvider(base_url=base_url)
  agent = agent_module.Agent(
    model=model_module.OllamaModel(model, provider=provider),
    output_type=str,
  )
  result = agent.run_sync(prompt)
  output = _extract_output(result)
  if not output.strip():
    raise LLMProviderOutputError("Ollama provider returned empty output.")
  return output


def _extract_output(result: Any) -> str:
  output = getattr(result, "output", None)
  if isinstance(output, str):
    return output
  if output is None:
    raise LLMProviderOutputError("LLM result did not expose textual output.")
  return str(output)
