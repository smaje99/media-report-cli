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
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner
from media_report.infrastructure.resources.templates import PackagePromptTemplateRepository


def process_command(
    path: Annotated[Path, typer.Argument(help="Media file or directory to process.")],
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Active in 0.1.0: scan subdirectories during discovery."),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Active in 0.1.0: reuse an existing artifact directory instead of failing.",
        ),
    ] = False,
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            help=(
                "Active in 0.1.0: override the planned LLM provider, metadata, "
                "and remote warning."
            ),
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            help="Active in 0.1.0: override the planned LLM model recorded in bootstrap metadata.",
        ),
    ] = None,
    language: Annotated[
        str | None,
        typer.Option(
            "--language",
            help="Stable roadmap placeholder: accepted now for future transcription selection.",
        ),
    ] = None,
    template: Annotated[
        str,
        typer.Option(
            "--template",
            help="Active in 0.1.0: choose the prompt template name stored in bootstrap metadata.",
        ),
    ] = "generic",
    output_format: Annotated[
        str | None,
        typer.Option(
            "--output-format",
            help=(
                "Active in 0.1.0 for planning: store the preferred output format "
                "for later stages."
            ),
        ),
    ] = None,
    only_transcribe: Annotated[
        bool,
        typer.Option(
            "--only-transcribe",
            help=(
                "Planning flag in 0.1.0: limit planned stages to "
                "extract_audio, normalize_audio, and transcribe."
            ),
        ),
    ] = False,
    only_report: Annotated[
        bool,
        typer.Option(
            "--only-report",
            help="Planning flag in 0.1.0: limit planned stages to report and pdf for later resume.",
        ),
    ] = False,
) -> None:
    """Prepare bootstrap artifacts, persist planning metadata, and print the planned stages."""
    settings = load_settings()
    scanner = FileSystemMediaScanner()
    templates = PackagePromptTemplateRepository()
    service = ProcessMediaService(scanner=scanner, templates=templates)

    try:
        plan = service.process(
            ProcessRequest(
                input_path=path,
                recursive=recursive,
                overwrite=overwrite,
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
    table.add_column("Stages")

    for item in plan.items:
        table.add_row(
            str(item.source.path),
            item.source.kind.value,
            str(item.artifacts.root_dir),
            item.template_name,
            ", ".join(stage.name for stage in item.stages),
        )

    console.print(table)
    console.print(
        f"Prepared {len(plan.items)} artifact director{'y' if len(plan.items) == 1 else 'ies'}."
    )
