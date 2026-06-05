from __future__ import annotations

from pathlib import Path

from media_report.application.reporting import PromptRenderService, RenderPromptRequest
from media_report.domain.artifacts.entities import PipelineStage
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaSource
from media_report.domain.transcription.entities import (
    TranscriptionResult,
    TranscriptionSegment,
)
from media_report.infrastructure.filesystem.metadata_repository import (
    JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner
from media_report.infrastructure.filesystem.transcription_repository import (
    JsonTranscriptionArtifactRepository,
)
from media_report.infrastructure.resources.templates import PackagePromptTemplateRepository


def build_transcription_result() -> TranscriptionResult:
    return TranscriptionResult(
        provider="faster-whisper",
        model="small",
        requested_language=None,
        detected_language="en",
        segments=(
            TranscriptionSegment(
                index=0,
                start_seconds=0.0,
                end_seconds=1.0,
                text="project status and next steps",
            ),
        ),
        duration_ms=80,
    )


def write_transcribed_artifact_root(media_path: Path) -> Path:
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(media_path)
    source = FileSystemMediaScanner().classify(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=source.kind),
        artifact_plan=artifact_plan,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language=None,
        selected_stages=tuple(PipelineStage),
    )
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    artifact_plan.audio_normalized.write_text("normalized", encoding="utf-8")
    JsonTranscriptionArtifactRepository().write(
        result=build_transcription_result(),
        transcript_raw_path=artifact_plan.transcript_raw,
        transcript_segments_path=artifact_plan.transcript_segments,
    )
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.EXTRACT_AUDIO)
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.NORMALIZE_AUDIO)
    metadata = planner.record_transcription(metadata, result=build_transcription_result())
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.TRANSCRIBE)
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    return artifact_plan.root_dir


def test_render_prompt_uses_packaged_prompt_templates(tmp_path: Path) -> None:
    media_path = tmp_path / "session.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_transcribed_artifact_root(media_path)
    service = PromptRenderService(
        scanner=FileSystemMediaScanner(),
        metadata_repository=JsonPipelineMetadataRepository(),
        template_repository=PackagePromptTemplateRepository(),
    )

    result = service.render_prompt(
        RenderPromptRequest(
            input_path=artifact_root,
            template_name="technical_report",
        )
    )

    assert (
        "Create a technical Markdown report with concise, factual language."
        in result.rendered_prompt
    )
    assert "project status and next steps" in result.rendered_prompt
    assert result.prompt_path.exists()
