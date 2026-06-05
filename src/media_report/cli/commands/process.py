from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape

from media_report.application.process_media.models import ProcessRequest
from media_report.cli.bootstrap import build_process_service
from media_report.cli.presentation.pipeline_runs import (
    build_process_runs_table,
    build_run_detail_lines,
)
from media_report.core.console import console
from media_report.core.errors import ArtifactConflictError, MediaReportError
from media_report.core.settings import load_settings


def process_command(
    path: Annotated[Path, typer.Argument(help="Media file or directory to process.")],
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Scan subdirectories during media discovery."),
    ] = False,
    resume: Annotated[
        bool,
        typer.Option(
            "--resume",
            help=(
                "Reuse a valid sibling artifact directory and execute only the stages "
                "still needed."
            ),
        ),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help=(
                "Deprecated alias for --resume in Sprint 2. "
                "A destructive overwrite is not exposed yet."
            ),
        ),
    ] = False,
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            help=(
                "Override the planned LLM provider recorded in metadata "
                "and used for remote warnings."
            ),
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model", help="Override the planned LLM model recorded in pipeline metadata."
        ),
    ] = None,
    language: Annotated[
        str | None,
        typer.Option(
            "--language", help="Record the requested transcription language in pipeline metadata."
        ),
    ] = None,
    template: Annotated[
        str,
        typer.Option(
            "--template", help="Choose the prompt template name stored in pipeline metadata."
        ),
    ] = "generic",
    output_format: Annotated[
        str | None,
        typer.Option(
            "--output-format", help="Store the preferred output format for later pipeline stages."
        ),
    ] = None,
    only_transcribe: Annotated[
        bool,
        typer.Option(
            "--only-transcribe",
            help="Limit planning to extract_audio, normalize_audio, and transcribe.",
        ),
    ] = False,
    only_report: Annotated[
        bool,
        typer.Option(
            "--only-report",
            help="Limit planning to report and pdf. Requires reusable transcription artifacts.",
        ),
    ] = False,
) -> None:
    """Process or resume local media through transcription-ready stages."""
    settings = load_settings()
    service = build_process_service(settings)

    try:
        plan = service.process(
            ProcessRequest(
                input_path=path,
                recursive=recursive,
                overwrite=overwrite,
                resume=resume,
                template_name=template,
                only_transcribe=only_transcribe,
                only_report=only_report,
                llm_provider=provider or settings.llm_provider,
                llm_model=model or settings.llm_model,
                language=language,
                transcription_device=settings.whisper_device,
                output_format=output_format or settings.output_format,
            )
        )
    except ArtifactConflictError as exc:
        console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(code=2) from exc
    except MediaReportError as exc:
        console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(code=1) from exc

    if overwrite:
        console.print(
            "[yellow]Warning:[/yellow] --overwrite is deprecated in Sprint 2 and currently behaves "
            "the same as --resume. A destructive overwrite mode will be introduced separately."
        )

    if plan.remote_provider_selected:
        console.print(
            "[yellow]Warning:[/yellow] remote provider selected. "
            "Transcripts may leave the local machine."
        )

    console.print(build_process_runs_table(plan.items))
    for item in plan.items:
        for line in build_run_detail_lines(
            source_name=item.source.path.name,
            stage_decisions=item.stage_decisions,
            metadata=item.final_metadata,
        ):
            console.print(line)
    console.print(
        f"Processed {len(plan.items)} artifact director{'y' if len(plan.items) == 1 else 'ies'}."
    )
