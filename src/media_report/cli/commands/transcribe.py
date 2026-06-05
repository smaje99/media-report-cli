from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape
from rich.table import Table

from media_report.application.transcribe.models import TranscribeRequest
from media_report.application.transcribe.service import TranscribeService
from media_report.core.console import console
from media_report.core.errors import MediaReportError
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
from media_report.infrastructure.transcription import FasterWhisperProvider


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
    service = TranscribeService(
        scanner=FileSystemMediaScanner(),
        metadata_repository=JsonPipelineMetadataRepository(),
        media_processor=FFmpegService(),
        transcription_provider=FasterWhisperProvider(default_model=settings.whisper_model),
        transcription_artifact_repository=JsonTranscriptionArtifactRepository(),
    )

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

    table = Table(title="Transcription Run")
    table.add_column("Source")
    table.add_column("Kind")
    table.add_column("Artifacts")
    table.add_column("Stage Decisions")
    table.add_column("Stage Status")
    table.add_column("Runtime")

    runtime = "-"
    if result.final_metadata.transcription is not None:
        transcription = result.final_metadata.transcription
        runtime = (
            f"{transcription.provider}/{transcription.model}\n"
            f"device={transcription.effective_device}"
        )
        if transcription.device_fallback_reason:
            runtime = f"{runtime}\n{transcription.device_fallback_reason}"

    table.add_row(
        str(result.source.path),
        result.source.kind.value,
        str(result.artifacts.root_dir),
        "\n".join(
            f"{decision.stage.value}: {decision.decision.value} ({decision.reason})"
            for decision in result.stage_decisions
        ),
        "\n".join(
            (
                f"extract_audio: "
                f"{result.final_metadata.stages[PipelineStage.EXTRACT_AUDIO].status.value}",
                f"normalize_audio: "
                f"{result.final_metadata.stages[PipelineStage.NORMALIZE_AUDIO].status.value}",
                f"transcribe: "
                f"{result.final_metadata.stages[PipelineStage.TRANSCRIBE].status.value}",
            )
        ),
        runtime,
    )
    console.print(table)

    for decision in result.stage_decisions:
        console.print(
            f"{result.source.path.name} :: {decision.stage.value}: "
            f"{decision.decision.value} - {decision.reason}"
        )
    for stage in (
        PipelineStage.EXTRACT_AUDIO,
        PipelineStage.NORMALIZE_AUDIO,
        PipelineStage.TRANSCRIBE,
    ):
        console.print(
            f"{result.source.path.name} :: {stage.value} status: "
            f"{result.final_metadata.stages[stage].status.value}"
        )
    if result.final_metadata.transcription is not None:
        transcription = result.final_metadata.transcription
        console.print(
            f"{result.source.path.name} :: transcription runtime: "
            f"{transcription.provider}/{transcription.model} "
            f"device={transcription.effective_device}"
        )
        if transcription.device_fallback_reason:
            console.print(
                f"{result.source.path.name} :: transcription fallback: "
                f"{transcription.device_fallback_reason}"
            )
    console.print("Processed 1 artifact directory.")
