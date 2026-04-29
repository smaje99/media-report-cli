from __future__ import annotations

from media_report.domain.reporting.ports import LLMProvider


class OllamaProvider(LLMProvider):
    def generate(self, prompt: str, *, model: str) -> str:
        raise NotImplementedError("Ollama integration is planned for a later phase.")
