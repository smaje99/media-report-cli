from __future__ import annotations

from pathlib import Path

from media_report.infrastructure.document.capabilities import get_pdf_capability


def test_pdf_capability_prefers_xelatex(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )
  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.shutil.which",
    lambda command: f"/usr/bin/{command}",
  )

  capability = get_pdf_capability()

  assert capability.available is True
  assert capability.engine == "xelatex"
  assert capability.warning is None
  assert "default.tex" in capability.detail


def test_pdf_capability_falls_back_to_lualatex(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )

  def fake_which(command: str) -> str | None:
    if command == "xelatex":
      return None
    return f"/usr/bin/{command}"

  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.shutil.which",
    fake_which,
  )

  capability = get_pdf_capability()

  assert capability.available is True
  assert capability.engine == "lualatex"
  assert capability.warning is not None


def test_pdf_capability_is_missing_without_pandoc(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )

  def fake_which(command: str) -> str | None:
    return None if command == "pandoc" else f"/usr/bin/{command}"

  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.shutil.which",
    fake_which,
  )

  capability = get_pdf_capability()

  assert capability.available is False
  assert capability.engine is None
  assert capability.install_hint is not None


def test_pdf_capability_is_missing_without_tex_engines(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.resolve_pdf_template_resource",
    lambda name="default.tex": Path(f"/tmp/{name}"),
  )

  def fake_which(command: str) -> str | None:
    return "/usr/bin/pandoc" if command == "pandoc" else None

  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.shutil.which",
    fake_which,
  )

  capability = get_pdf_capability()

  assert capability.available is False
  assert capability.engine is None
  assert "xelatex" in capability.detail
  assert capability.install_hint is not None


def test_pdf_capability_is_missing_when_template_cannot_be_resolved(monkeypatch) -> None:
  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.shutil.which",
    lambda command: f"/usr/bin/{command}",
  )

  def raise_missing(name: str = "default.tex") -> Path:
    raise FileNotFoundError(name)

  monkeypatch.setattr(
    "media_report.infrastructure.document.capabilities.resolve_pdf_template_resource",
    raise_missing,
  )

  capability = get_pdf_capability()

  assert capability.available is False
  assert capability.engine == "xelatex"
  assert "default.tex" in capability.detail
