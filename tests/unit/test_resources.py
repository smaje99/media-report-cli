from media_report.core.resources import (
    list_pdf_templates,
    list_prompt_templates,
    load_prompt_template,
)


def test_prompt_template_loading() -> None:
    template = load_prompt_template("generic")

    assert "Executive Summary" in template


def test_template_listing() -> None:
    assert "generic" in list_prompt_templates()
    assert "default.tex" in list_pdf_templates()
