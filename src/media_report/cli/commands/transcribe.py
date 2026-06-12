from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape

from media_report.application.transcribe.models import TranscribeRequest
from media_report.cli.bootstrap import build_transcribe_service
from media_report.cli.presentation.pipeline_runs import (
  build_run_detail_lines,
  build_transcribe_run_table,
)
from media_report.core.console import console
from media_report.core.errors import MediaReportError
from media_report.core.settings import load_settings


def transcribe_command(
  path: Annotated[
    Path,
    typer.Argument(help="Media file or artifact directory to transcribe."),
  ],
  language: Annotated[
    str | None,
    typer.Option("--language", help="Override the requested transcription language."),
  ] = None,
  model: Annotated[
    str | None,
    typer.Option("--model", help="Override the transcription model for this run."),
  ] = None,
  overwrite: Annotated[
    bool,
    typer.Option(
      "--overwrite",
      help="Re-run only the transcribe stage when reusable audio artifacts already exist.",
    ),
  ] = False,
) -> None:
  """Transcribe a media file or reusable artifact directory."""
  settings = load_settings()
  service = build_transcribe_service(settings)

  try:
    result = service.transcribe(
      TranscribeRequest(
        input_path=path,
        overwrite=overwrite,
        language=language,
        transcription_model_override=model,
        device_preference=settings.whisper_device,
        workflow_llm_provider=settings.llm_provider,
        workflow_llm_model=settings.llm_model,
        workflow_output_format=settings.output_format,
      )
    )
  except MediaReportError as exc:
    console.print(f"[red]Error:[/red] {escape(str(exc))}")
    raise typer.Exit(code=1) from exc

  console.print(build_transcribe_run_table(result))
  for line in build_run_detail_lines(
    source_name=result.source.path.name,
    stage_decisions=result.stage_decisions,
    metadata=result.final_metadata,
  ):
    console.print(line)
  console.print("Processed 1 artifact directory.")
