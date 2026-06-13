from media_report.core.resources import (
  list_pdf_templates,
  list_prompt_templates,
  load_prompt_template,
  resolve_pdf_template_resource,
)


def test_prompt_template_loading() -> None:
  template = load_prompt_template("generic")

  assert "Executive Summary" in template


def test_template_listing() -> None:
  assert "generic" in list_prompt_templates()
  assert "default.tex" in list_pdf_templates()


def test_pdf_template_resource_resolution() -> None:
  resource = resolve_pdf_template_resource()

  assert resource.name == "default.tex"
