from __future__ import annotations

import shutil
import subprocess
from importlib.resources import as_file
from pathlib import Path

from media_report.core.errors import (
  PDFRenderingConfigurationError,
  PDFRenderingExecutionError,
  PDFRenderingOutputError,
)
from media_report.core.redaction import redact_text
from media_report.core.resources import resolve_pdf_template_resource

from .capabilities import PREFERRED_PDF_ENGINES
from .pandoc_service import PandocService


class PandocDocumentRenderer:
  def __init__(self) -> None:
    self.last_engine: str | None = None

  @property
  def preferred_engine(self) -> str:
    for engine in PREFERRED_PDF_ENGINES:
      if shutil.which(engine) is not None:
        return engine
    raise PDFRenderingConfigurationError(
      "No supported TeX engine is available in PATH. Install xelatex or lualatex."
    )

  def render(self, markdown_path: Path, pdf_path: Path) -> None:
    if shutil.which("pandoc") is None:
      raise PDFRenderingConfigurationError("pandoc command not found in PATH.")

    with as_file(resolve_pdf_template_resource()) as template_path:
      first_engine = self.preferred_engine
      try:
        self._render_with_engine(
          markdown_path=markdown_path,
          pdf_path=pdf_path,
          template_path=template_path,
          engine=first_engine,
        )
        return
      except PDFRenderingExecutionError as exc:
        if (
          first_engine == "xelatex"
          and self._should_fallback(exc.stderr_summary)
          and shutil.which("lualatex") is not None
        ):
          self._render_with_engine(
            markdown_path=markdown_path,
            pdf_path=pdf_path,
            template_path=template_path,
            engine="lualatex",
          )
          return
        raise

  def _render_with_engine(
    self,
    *,
    markdown_path: Path,
    pdf_path: Path,
    template_path: Path,
    engine: str,
  ) -> None:
    self.last_engine = engine
    command = PandocService.build_command(
      markdown_path,
      pdf_path,
      template_path,
      engine=engine,
    )
    completed = subprocess.run(
      command,
      capture_output=True,
      text=True,
      check=False,
    )
    if completed.returncode != 0:
      stderr_summary = _summarize_stderr(completed.stderr)
      raise PDFRenderingExecutionError(
        engine=engine,
        exit_code=completed.returncode,
        stderr_summary=stderr_summary,
      )
    if not pdf_path.exists():
      raise PDFRenderingOutputError(
        f"Pandoc completed with engine '{engine}' but did not produce '{pdf_path.name}'."
      )

  @staticmethod
  def _should_fallback(stderr_summary: str | None) -> bool:
    if stderr_summary is None:
      return False
    lowered = stderr_summary.lower()
    return any(
      marker in lowered
      for marker in (
        "not found",
        "could not find executable",
        "unknown pdf engine",
        "pdf-engine",
        "not available",
      )
    )


def _summarize_stderr(stderr: str) -> str | None:
  text = redact_text(stderr.strip())
  if not text:
    return None
  summary = " ".join(text.split())
  return summary[:280]
