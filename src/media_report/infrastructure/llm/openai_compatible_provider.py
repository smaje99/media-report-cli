from __future__ import annotations

from media_report.domain.reporting.ports import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    def generate(self, prompt: str, *, model: str) -> str:
        raise NotImplementedError("OpenAI-compatible integration is planned for a later phase.")
