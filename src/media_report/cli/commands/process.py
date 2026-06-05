from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape
from rich.table import Table

from media_report.application.process_media.models import ProcessRequest
from media_report.application.process_media.service import ProcessMediaService
from media_report.application.transcribe.service import TranscribeService
from media_report.core.console import console
from media_report.core.errors import ArtifactConflictError, MediaReportError
from media_report.core.settings import load_settings
from media_report.domain.artifacts.entities import PipelineStage
from media_report.infrastructure.ffmpeg.service import FFmpegService
from media_report.infrastructure.filesystem.metadata_repository import (
    JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner
from media_report.infrastructure.filesystem.transcription_repository import (
    JsonTranscriptionArtifactRepository,
)
from media_report.infrastructure.resources.templates import PackagePromptTemplateRepository
from media_report.infrastructure.transcription import FasterWhisperProvider


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
    scanner = FileSystemMediaScanner()
    templates = PackagePromptTemplateRepository()
    metadata_repository = JsonPipelineMetadataRepository()
    media_processor = FFmpegService()
    transcribe_service = TranscribeService(
        scanner=scanner,
        metadata_repository=metadata_repository,
        media_processor=media_processor,
        transcription_provider=FasterWhisperProvider(default_model=settings.whisper_model),
        transcription_artifact_repository=JsonTranscriptionArtifactRepository(),
    )
    service = ProcessMediaService(
        scanner=scanner,
        templates=templates,
        metadata_repository=metadata_repository,
        transcribe_service=transcribe_service,
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

    table = Table(title="Media Runs")
    table.add_column("Source")
    table.add_column("Kind")
    table.add_column("Artifacts")
    table.add_column("Template")
    table.add_column("Stage Decisions")
    table.add_column("Stage Status")
    table.add_column("Runtime")

    for item in plan.items:
        runtime = "-"
        if item.final_metadata.transcription is not None:
            transcription = item.final_metadata.transcription
            runtime = (
                f"{transcription.provider}/{transcription.model}\n"
                f"device={transcription.effective_device}"
            )
            if transcription.device_fallback_reason:
                runtime = f"{runtime}\n{transcription.device_fallback_reason}"
        table.add_row(
            str(item.source.path),
            item.source.kind.value,
            str(item.artifacts.root_dir),
            item.template_name,
            "\n".join(
                f"{decision.stage.value}: {decision.decision.value} ({decision.reason})"
                for decision in item.stage_decisions
            ),
            "\n".join(
                (
                    f"extract_audio: "
                    f"{item.final_metadata.stages[PipelineStage.EXTRACT_AUDIO].status.value}",
                    f"normalize_audio: "
                    f"{item.final_metadata.stages[PipelineStage.NORMALIZE_AUDIO].status.value}",
                    f"transcribe: "
                    f"{item.final_metadata.stages[PipelineStage.TRANSCRIBE].status.value}",
                )
            ),
            runtime,
        )

    console.print(table)
    for item in plan.items:
        for decision in item.stage_decisions:
            console.print(
                f"{item.source.path.name} :: {decision.stage.value}: "
                f"{decision.decision.value} - {decision.reason}"
            )
        console.print(
            f"{item.source.path.name} :: extract_audio status: "
            f"{item.final_metadata.stages[PipelineStage.EXTRACT_AUDIO].status.value}"
        )
        console.print(
            f"{item.source.path.name} :: normalize_audio status: "
            f"{item.final_metadata.stages[PipelineStage.NORMALIZE_AUDIO].status.value}"
        )
        console.print(
            f"{item.source.path.name} :: transcribe status: "
            f"{item.final_metadata.stages[PipelineStage.TRANSCRIBE].status.value}"
        )
        if item.final_metadata.transcription is not None:
            transcription = item.final_metadata.transcription
            console.print(
                f"{item.source.path.name} :: transcription runtime: "
                f"{transcription.provider}/{transcription.model} "
                f"device={transcription.effective_device}"
            )
            if transcription.device_fallback_reason:
                console.print(
                    f"{item.source.path.name} :: transcription fallback: "
                    f"{transcription.device_fallback_reason}"
                )
    console.print(
        f"Processed {len(plan.items)} artifact director{'y' if len(plan.items) == 1 else 'ies'}."
    )
