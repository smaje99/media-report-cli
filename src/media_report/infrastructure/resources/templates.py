from __future__ import annotations

from media_report.core.resources import load_prompt_template
from media_report.domain.reporting.ports import PromptTemplateRepository


class PackagePromptTemplateRepository(PromptTemplateRepository):
    def get_template(self, name: str) -> str:
        return load_prompt_template(name)
