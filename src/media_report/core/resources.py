from __future__ import annotations

from importlib.resources import files

from media_report.core.errors import TemplateNotFoundError


def _resource_names(package: str, suffix: str) -> list[str]:
    root = files(package)
    return sorted(
        item.name
        for item in root.iterdir()
        if item.is_file() and item.name.endswith(suffix)
    )


def list_prompt_templates() -> list[str]:
    return [
        name.removesuffix(".md")
        for name in _resource_names("media_report.templates.prompts", ".md")
    ]


def list_pdf_templates() -> list[str]:
    return _resource_names("media_report.templates.pdf", ".tex")


def load_prompt_template(name: str) -> str:
    resource = files("media_report.templates.prompts").joinpath(f"{name}.md")
    if not resource.is_file():
        raise TemplateNotFoundError(f"Prompt template '{name}' was not found.")
    return resource.read_text(encoding="utf-8")
