from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from media_report.application.process_media.models import ProcessRequest
from media_report.application.process_media.service import ProcessMediaService
from media_report.core.console import console
from media_report.core.errors import ArtifactConflictError, MediaReportError
from media_report.core.settings import load_settings
from media_report.infrastructure.filesystem.metadata_repository import (
    JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner
from media_report.infrastructure.resources.templates import PackagePromptTemplateRepository


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
            help="Reuse a valid sibling artifact directory and plan only the stages still needed.",
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
    """Prepare or resume artifact planning, persist metadata, and print per-stage decisions."""
    settings = load_settings()
    scanner = FileSystemMediaScanner()
    templates = PackagePromptTemplateRepository()
    metadata_repository = JsonPipelineMetadataRepository()
    service = ProcessMediaService(
        scanner=scanner,
        templates=templates,
        metadata_repository=metadata_repository,
    )

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
                output_format=output_format or settings.output_format,
            )
        )
    except ArtifactConflictError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    except MediaReportError as exc:
        console.print(f"[red]Error:[/red] {exc}")
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

    table = Table(title="Planned Media Runs")
    table.add_column("Source")
    table.add_column("Kind")
    table.add_column("Artifacts")
    table.add_column("Template")
    table.add_column("Stage Decisions")

    for item in plan.items:
        table.add_row(
            str(item.source.path),
            item.source.kind.value,
            str(item.artifacts.root_dir),
            item.template_name,
            "\n".join(
                f"{decision.stage.value}: {decision.decision.value} ({decision.reason})"
                for decision in item.stage_decisions
            ),
        )

    console.print(table)
    for item in plan.items:
        for decision in item.stage_decisions:
            console.print(
                f"{item.source.path.name} :: {decision.stage.value}: "
                f"{decision.decision.value} - {decision.reason}"
            )
    console.print(
        f"Prepared {len(plan.items)} artifact director{'y' if len(plan.items) == 1 else 'ies'}."
    )
