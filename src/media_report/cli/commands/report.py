from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape

from media_report.application.reporting import GenerateReportRequest
from media_report.cli.bootstrap import build_report_generation_service
from media_report.cli.presentation.pipeline_runs import (
  REPORT_DISPLAY_STAGES,
  build_report_run_table,
  build_run_detail_lines,
)
from media_report.core.console import console
from media_report.core.errors import InputPathError, MediaReportError, ResumeNotPossibleError
from media_report.core.settings import load_settings
from media_report.domain.artifacts.service import ArtifactPlanner


def report_command(
  path: Annotated[
    Path,
    typer.Argument(help="Artifact directory or media file with reusable report artifacts."),
  ],
  template: Annotated[
    str | None,
    typer.Option("--template", help="Override the prompt template for this report run."),
  ] = None,
  provider: Annotated[
    str | None,
    typer.Option("--provider", help="Override the LLM provider for this report run."),
  ] = None,
  model: Annotated[
    str | None,
    typer.Option("--model", help="Override the LLM model for this report run."),
  ] = None,
  overwrite: Annotated[
    bool,
    typer.Option(
      "--overwrite",
      help="Re-run only the report stage when reusable transcription artifacts already exist.",
    ),
  ] = False,
) -> None:
  """Generate a report from a reusable artifact directory."""
  settings = load_settings()
  service = build_report_generation_service(settings)

  try:
    artifact_root = _resolve_report_input_path(path)
    result = service.generate_report(
      GenerateReportRequest(
        input_path=artifact_root,
        template_name=template,
        llm_provider=provider or settings.llm_provider,
        llm_model=model or settings.llm_model,
        overwrite=overwrite,
      )
    )
  except MediaReportError as exc:
    console.print(f"[red]Error:[/red] {escape(str(exc))}")
    raise typer.Exit(code=1) from exc

  if result.remote_provider_selected:
    console.print(
      "[yellow]Warning:[/yellow] remote provider selected. Transcripts may leave the local machine."
    )

  console.print(build_report_run_table(result))
  for line in build_run_detail_lines(
    source_name=result.source.path.name,
    stage_decisions=result.stage_decisions,
    metadata=result.final_metadata,
    visible_stages=REPORT_DISPLAY_STAGES,
  ):
    console.print(line)
  console.print("Processed 1 artifact directory.")


def _resolve_report_input_path(path: Path) -> Path:
  if not path.exists():
    raise InputPathError(f"Input path does not exist: {path}")
  if path.is_dir():
    return path
  if not path.is_file():
    raise InputPathError(f"Input path is not a file or directory: {path}")

  artifact_root = ArtifactPlanner().plan(path).root_dir
  if artifact_root.exists():
    return artifact_root
  raise ResumeNotPossibleError(
    f"No existing artifact directory was found for '{path.name}'. "
    "Run 'media-report process PATH' or 'media-report transcribe PATH' first."
  )
