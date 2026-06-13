from __future__ import annotations

import platform
import shutil

from rich.markup import escape
from rich.table import Table

from media_report.core.console import console
from media_report.core.resources import list_pdf_templates, list_prompt_templates
from media_report.core.settings import load_settings, redact_settings
from media_report.infrastructure.llm import get_llm_capability
from media_report.infrastructure.transcription import get_transcription_capability


def doctor_command() -> None:
  """Inspect bootstrap dependencies, packaged templates, and effective configuration."""
  settings = load_settings()
  table = Table(title="media-report doctor")
  table.add_column("Check")
  table.add_column("Status")
  table.add_column("Details")

  os_name = platform.system().lower()
  if os_name in {"linux", "darwin"}:
    table.add_row("platform", "ok", f"{platform.system()} is an official target")
  else:
    table.add_row(
      "platform",
      "warning",
      f"{platform.system()} is experimental for 0.1.0",
    )

  for command in ("ffmpeg", "pandoc", "xelatex", "lualatex", "ollama"):
    resolved = shutil.which(command)
    table.add_row(
      f"cmd:{command}",
      "ok" if resolved else "missing",
      resolved or "not found in PATH",
    )

  transcription = get_transcription_capability()
  table.add_row(
    "transcription",
    "ok" if transcription.available else "missing",
    escape(
      f"{transcription.provider}: {transcription.detail}"
      if transcription.available
      else f"{transcription.provider}: {transcription.install_hint}"
    ),
  )

  llm = get_llm_capability(settings)
  llm_status = "ok"
  if not llm.available:
    llm_status = "missing"
  elif llm.is_remote:
    llm_status = "warning"
  llm_details = llm.detail
  if llm.warning:
    llm_details = f"{llm_details} {llm.warning}"
  table.add_row("llm", llm_status, escape(f"{llm.provider}: {llm_details}"))

  table.add_row("prompt templates", "ok", ", ".join(list_prompt_templates()))
  table.add_row("pdf templates", "ok", ", ".join(list_pdf_templates()))

  config_state = "present" if settings.config_path.exists() else "missing"
  table.add_row("config file", config_state, str(settings.config_path))

  api_status = "configured" if settings.openai_api_key else "not configured"
  table.add_row("openai api key", api_status, redact_settings(settings)["openai_api_key"])

  console.print(table)
