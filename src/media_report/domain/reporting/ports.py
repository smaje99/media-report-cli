from __future__ import annotations

from pathlib import Path
from typing import Protocol


class PromptTemplateRepository(Protocol):
    def get_template(self, name: str) -> str:
        """Return the prompt template content for the given logical name."""


class LLMProvider(Protocol):
    def generate(self, prompt: str, *, model: str) -> str:
        """Generate a Markdown report from a prompt."""


class DocumentRenderer(Protocol):
    def render(self, markdown_path: Path, pdf_path: Path) -> None:
        """Render Markdown to PDF."""
