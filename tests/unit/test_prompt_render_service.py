from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_report.application.reporting import PromptRenderService, RenderPromptRequest
from media_report.core.errors import PromptRenderPrerequisiteError, TemplateNotFoundError
from media_report.domain.artifacts.entities import PipelineStage, PipelineStageStatus
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaSource
from media_report.domain.reporting.ports import PromptTemplateRepository
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


class StubTemplateRepository:
    def get_template(self, name: str) -> str:
        if name == "missing":
            raise FileNotFoundError(name)
        return f"# Template {name}\n\nFollow the transcript carefully."


class MissingTemplateRepository:
    def get_template(self, name: str) -> str:
        raise TemplateNotFoundError(f"Prompt template '{name}' was not found.")


def build_service(
    template_repository: PromptTemplateRepository | None = None,
) -> PromptRenderService:
    effective_template_repository = (
        template_repository if template_repository is not None else StubTemplateRepository()
    )
    return PromptRenderService(
        scanner=FileSystemMediaScanner(),
        metadata_repository=JsonPipelineMetadataRepository(),
        template_repository=effective_template_repository,
    )


def build_transcription_result(text: str = "hola mundo") -> TranscriptionResult:
    return TranscriptionResult(
        provider="faster-whisper",
        model="small",
        requested_language="es",
        detected_language="es",
        segments=(
            TranscriptionSegment(
                index=0,
                start_seconds=0.0,
                end_seconds=1.0,
                text=text,
            ),
        ),
        duration_ms=120,
        device_preference="auto",
        effective_device="cpu",
    )


def write_transcribed_artifact_root(media_path: Path, transcript_text: str = "hola mundo") -> Path:
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
        language="es",
        selected_stages=tuple(PipelineStage),
    )
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    artifact_plan.audio_normalized.write_text("normalized", encoding="utf-8")
    JsonTranscriptionArtifactRepository().write(
        result=build_transcription_result(text=transcript_text),
        transcript_raw_path=artifact_plan.transcript_raw,
        transcript_segments_path=artifact_plan.transcript_segments,
    )
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.EXTRACT_AUDIO)
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.NORMALIZE_AUDIO)
    metadata = planner.record_transcription(
        metadata,
        result=build_transcription_result(text=transcript_text),
    )
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.TRANSCRIBE)
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    return artifact_plan.root_dir


def test_render_prompt_persists_prompt_and_keeps_report_planned(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_transcribed_artifact_root(media_path)

    result = build_service().render_prompt(RenderPromptRequest(input_path=artifact_root))

    prompt_text = result.prompt_path.read_text(encoding="utf-8")
    assert result.prompt_path == artifact_root / "prompt_used.md"
    assert result.rendered_prompt == prompt_text
    assert "## Template Instructions" in prompt_text
    assert "## Transcript" in prompt_text
    assert "hola mundo" in prompt_text
    assert result.final_metadata.workflow.template_name == "generic"
    assert result.final_metadata.stages[PipelineStage.REPORT].status == PipelineStageStatus.PLANNED
    assert "report prompt rendered" in (artifact_root / "pipeline.log").read_text(encoding="utf-8")


def test_render_prompt_updates_template_name_when_overridden(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_transcribed_artifact_root(media_path)

    result = build_service().render_prompt(
        RenderPromptRequest(
            input_path=artifact_root,
            template_name="meeting",
        )
    )

    assert result.final_metadata.workflow.template_name == "meeting"
    assert "# Prompt Template: meeting" in result.rendered_prompt
    metadata_payload = json.loads((artifact_root / "metadata.json").read_text(encoding="utf-8"))
    assert metadata_payload["workflow"]["template_name"] == "meeting"


def test_render_prompt_marks_report_failed_when_template_is_missing(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_transcribed_artifact_root(media_path)
    service = build_service(MissingTemplateRepository())

    with pytest.raises(PromptRenderPrerequisiteError):
        service.render_prompt(RenderPromptRequest(input_path=artifact_root))

    metadata_payload = json.loads((artifact_root / "metadata.json").read_text(encoding="utf-8"))
    assert metadata_payload["stages"]["report"]["status"] == "failed"
    assert metadata_payload["stages"]["report"]["error"]["code"] == "prompt_render_prerequisite"


def test_render_prompt_rejects_blank_transcript(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_transcribed_artifact_root(media_path)
    (artifact_root / "transcript_raw.txt").write_text("", encoding="utf-8")

    with pytest.raises(PromptRenderPrerequisiteError):
        build_service().render_prompt(RenderPromptRequest(input_path=artifact_root))


def test_render_prompt_rejects_invalid_transcript_segments(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_transcribed_artifact_root(media_path)
    (artifact_root / "transcript_segments.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(PromptRenderPrerequisiteError):
        build_service().render_prompt(RenderPromptRequest(input_path=artifact_root))
