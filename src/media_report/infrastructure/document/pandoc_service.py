from __future__ import annotations

from pathlib import Path


class PandocService:
  @staticmethod
  def build_command(
    markdown_path: Path,
    pdf_path: Path,
    template_path: Path,
    *,
    engine: str,
  ) -> list[str]:
    return [
      "pandoc",
      str(markdown_path),
      f"--pdf-engine={engine}",
      f"--template={template_path}",
      "-o",
      str(pdf_path),
    ]
