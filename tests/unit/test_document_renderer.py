from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from media_report.core.errors import (
  PDFRenderingConfigurationError,
  PDFRenderingExecutionError,
  PDFRenderingOutputError,
)
from media_report.infrastructure.document.pandoc_renderer import PandocDocumentRenderer


def test_renderer_uses_xelatex_when_available(tmp_path: Path, monkeypatch) -> None:
  markdown_path = tmp_path / "report.md"
  pdf_path = tmp_path / "report.pdf"
  markdown_path.write_text("# Report\n", encoding="utf-8")

  commands: list[list[str]] = []

  def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
    commands.append(command)
    pdf_path.write_text("pdf", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, "", "")

  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.shutil.which",
    lambda command: f"/usr/bin/{command}",
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.subprocess.run",
    fake_run,
  )

  renderer = PandocDocumentRenderer()
  renderer.render(markdown_path, pdf_path)

  assert len(commands) == 1
  assert "--pdf-engine=xelatex" in commands[0]


def test_renderer_falls_back_to_lualatex_when_xelatex_is_missing(
  tmp_path: Path, monkeypatch
) -> None:
  markdown_path = tmp_path / "report.md"
  pdf_path = tmp_path / "report.pdf"
  markdown_path.write_text("# Report\n", encoding="utf-8")

  commands: list[list[str]] = []

  def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
    commands.append(command)
    pdf_path.write_text("pdf", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, "", "")

  def fake_which(command: str) -> str | None:
    return None if command == "xelatex" else f"/usr/bin/{command}"

  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.shutil.which",
    fake_which,
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.subprocess.run",
    fake_run,
  )

  renderer = PandocDocumentRenderer()
  renderer.render(markdown_path, pdf_path)

  assert len(commands) == 1
  assert "--pdf-engine=lualatex" in commands[0]


def test_renderer_does_not_fallback_on_arbitrary_render_failure(
  tmp_path: Path, monkeypatch
) -> None:
  markdown_path = tmp_path / "report.md"
  pdf_path = tmp_path / "report.pdf"
  markdown_path.write_text("# Report\n", encoding="utf-8")

  commands: list[list[str]] = []

  def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
    commands.append(command)
    return subprocess.CompletedProcess(command, 43, "", "LaTeX Error: broken template")

  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.shutil.which",
    lambda command: f"/usr/bin/{command}",
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.subprocess.run",
    fake_run,
  )

  renderer = PandocDocumentRenderer()

  with pytest.raises(PDFRenderingExecutionError) as exc_info:
    renderer.render(markdown_path, pdf_path)

  assert len(commands) == 1
  assert exc_info.value.engine == "xelatex"
  assert exc_info.value.exit_code == 43


def test_renderer_raises_when_pdf_output_is_missing(tmp_path: Path, monkeypatch) -> None:
  markdown_path = tmp_path / "report.md"
  pdf_path = tmp_path / "report.pdf"
  markdown_path.write_text("# Report\n", encoding="utf-8")

  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.shutil.which",
    lambda command: f"/usr/bin/{command}",
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.subprocess.run",
    lambda command, **_: subprocess.CompletedProcess(command, 0, "", ""),
  )

  renderer = PandocDocumentRenderer()

  with pytest.raises(PDFRenderingOutputError):
    renderer.render(markdown_path, pdf_path)


def test_renderer_raises_configuration_error_when_no_tex_engine_is_available(
  tmp_path: Path, monkeypatch
) -> None:
  markdown_path = tmp_path / "report.md"
  pdf_path = tmp_path / "report.pdf"
  markdown_path.write_text("# Report\n", encoding="utf-8")

  def fake_which(command: str) -> str | None:
    return "/usr/bin/pandoc" if command == "pandoc" else None

  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.shutil.which",
    fake_which,
  )

  renderer = PandocDocumentRenderer()

  with pytest.raises(PDFRenderingConfigurationError):
    renderer.render(markdown_path, pdf_path)


def test_renderer_falls_back_when_engine_cannot_be_selected(tmp_path: Path, monkeypatch) -> None:
  markdown_path = tmp_path / "report.md"
  pdf_path = tmp_path / "report.pdf"
  markdown_path.write_text("# Report\n", encoding="utf-8")

  commands: list[list[str]] = []

  def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
    commands.append(command)
    if "--pdf-engine=xelatex" in command:
      return subprocess.CompletedProcess(
        command,
        47,
        "",
        "pdf-engine xelatex not found",
      )
    pdf_path.write_text("pdf", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, "", "")

  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.shutil.which",
    lambda command: f"/usr/bin/{command}",
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.pandoc_renderer.subprocess.run",
    fake_run,
  )

  renderer = PandocDocumentRenderer()
  renderer.render(markdown_path, pdf_path)

  assert len(commands) == 2
  assert "--pdf-engine=xelatex" in commands[0]
  assert "--pdf-engine=lualatex" in commands[1]
