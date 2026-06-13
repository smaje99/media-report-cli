from __future__ import annotations

import shutil

from pydantic import BaseModel, ConfigDict

from media_report.core.errors import TemplateNotFoundError
from media_report.core.resources import resolve_pdf_template_resource

PDF_TEMPLATE_NAME = "default.tex"
PDF_INSTALL_HINT = "Install pandoc and either xelatex or lualatex, then rerun doctor."
PREFERRED_PDF_ENGINES = ("xelatex", "lualatex")


class PDFCapability(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  available: bool
  detail: str
  engine: str | None
  template: str
  warning: str | None = None
  install_hint: str | None = None


def get_pdf_capability() -> PDFCapability:
  template_name = PDF_TEMPLATE_NAME
  template_detail = template_name

  try:
    resolve_pdf_template_resource(template_name)
  except (TemplateNotFoundError, FileNotFoundError) as exc:
    engine = _detect_engine()
    return PDFCapability(
      available=False,
      detail=f"PDF template '{template_name}' is not resolvable: {exc}",
      engine=engine,
      template=template_detail,
    )

  if shutil.which("pandoc") is None:
    return PDFCapability(
      available=False,
      detail="pandoc command not found in PATH.",
      engine=None,
      template=template_detail,
      install_hint=PDF_INSTALL_HINT,
    )

  engine = _detect_engine()
  if engine is None:
    return PDFCapability(
      available=False,
      detail="No supported TeX engine found in PATH. Tried xelatex and lualatex.",
      engine=None,
      template=template_detail,
      install_hint=PDF_INSTALL_HINT,
    )

  warning = None
  if engine == "lualatex":
    warning = "xelatex not found; using lualatex fallback."

  return PDFCapability(
    available=True,
    detail=f"pandoc with {engine} using {template_name}",
    engine=engine,
    template=template_detail,
    warning=warning,
  )


def _detect_engine() -> str | None:
  return next(
    (engine for engine in PREFERRED_PDF_ENGINES if shutil.which(engine) is not None),
    None,
  )
