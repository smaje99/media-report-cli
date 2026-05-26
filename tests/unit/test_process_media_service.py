from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from media_report.application.process_media.models import ProcessRequest
from media_report.application.process_media.service import ProcessMediaService
from media_report.core.errors import MediaProcessingExecutionError
from media_report.domain.artifacts.entities import PipelineStage, PipelineStageStatus
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import (
    ExtractAudioRequest,
    MediaProcessingResult,
    MediaSource,
    NormalizeAudioRequest,
)
from media_report.infrastructure.filesystem.metadata_repository import (
    JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


class StubTemplateRepository:
    def get_template(self, name: str) -> str:
        return f"template:{name}"


class StubMediaProcessor:
    def __init__(self, *, fail_normalize: bool = False) -> None:
        self.fail_normalize = fail_normalize
        self.calls: list[str] = []

    def extract_audio(self, request: ExtractAudioRequest) -> MediaProcessingResult:
        self.calls.append("extract_audio")
        request.output_path.write_text("audio", encoding="utf-8")
        return MediaProcessingResult(
            output_path=request.output_path,
            command=("ffmpeg", "-i", str(request.source.path), str(request.output_path)),
            duration_ms=12,
            stderr_summary=None,
        )

    def normalize_audio(self, request: NormalizeAudioRequest) -> MediaProcessingResult:
        self.calls.append("normalize_audio")
        if self.fail_normalize:
            raise MediaProcessingExecutionError(
                operation="normalize_audio",
                exit_code=1,
                stderr_summary="normalization failed",
            )
        request.output_path.write_text("normalized", encoding="utf-8")
        return MediaProcessingResult(
            output_path=request.output_path,
            command=("ffmpeg", "-i", str(request.source_path), str(request.output_path)),
            duration_ms=15,
            stderr_summary=None,
        )


def build_service(media_processor: StubMediaProcessor) -> ProcessMediaService:
    return ProcessMediaService(
        scanner=FileSystemMediaScanner(),
        templates=StubTemplateRepository(),
        metadata_repository=JsonPipelineMetadataRepository(),
        media_processor=media_processor,
    )


def write_extract_ready_metadata(media_path: Path) -> Path:
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
    metadata = replace(
        metadata,
        stages={
            **metadata.stages,
            PipelineStage.EXTRACT_AUDIO: replace(
                metadata.stages[PipelineStage.EXTRACT_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
        },
    )
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    return artifact_plan.root_dir


def write_resume_ready_metadata(media_path: Path) -> Path:
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
    metadata = replace(
        metadata,
        stages={
            **metadata.stages,
            PipelineStage.EXTRACT_AUDIO: replace(
                metadata.stages[PipelineStage.EXTRACT_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
            PipelineStage.NORMALIZE_AUDIO: replace(
                metadata.stages[PipelineStage.NORMALIZE_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
            PipelineStage.TRANSCRIBE: replace(
                metadata.stages[PipelineStage.TRANSCRIBE],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
        },
    )
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    artifact_plan.audio_normalized.write_text("normalized", encoding="utf-8")
    artifact_plan.transcript_raw.write_text("transcript", encoding="utf-8")
    artifact_plan.transcript_segments.write_text("[]", encoding="utf-8")
    return artifact_plan.root_dir


def test_process_executes_audio_prep_for_new_run(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    media_processor = StubMediaProcessor()
    service = build_service(media_processor)

    plan = service.process(ProcessRequest(input_path=media_path))

    assert media_processor.calls == ["extract_audio", "normalize_audio"]
    item = plan.items[0]
    assert (
        item.final_metadata.stages[PipelineStage.EXTRACT_AUDIO].status
        == PipelineStageStatus.COMPLETED
    )
    assert (
        item.final_metadata.stages[PipelineStage.NORMALIZE_AUDIO].status
        == PipelineStageStatus.COMPLETED
    )
    assert (
        item.final_metadata.stages[PipelineStage.TRANSCRIBE].status
        == PipelineStageStatus.PLANNED
    )
    assert item.artifacts.audio_extracted.exists()
    assert item.artifacts.audio_normalized.exists()


def test_process_resume_reuses_extract_and_executes_only_normalize(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    write_extract_ready_metadata(media_path)
    media_processor = StubMediaProcessor()
    service = build_service(media_processor)

    plan = service.process(ProcessRequest(input_path=media_path, resume=True))

    assert media_processor.calls == ["normalize_audio"]
    item = plan.items[0]
    assert (
        item.final_metadata.stages[PipelineStage.EXTRACT_AUDIO].status
        == PipelineStageStatus.COMPLETED
    )
    assert (
        item.final_metadata.stages[PipelineStage.NORMALIZE_AUDIO].status
        == PipelineStageStatus.COMPLETED
    )


def test_process_persists_failed_normalize_and_preserves_extracted_audio(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    media_processor = StubMediaProcessor(fail_normalize=True)
    service = build_service(media_processor)
    artifact_dir = media_path.parent / f"{media_path.stem}_media_report"

    with pytest.raises(MediaProcessingExecutionError):
        service.process(ProcessRequest(input_path=media_path))

    metadata = JsonPipelineMetadataRepository().read(artifact_dir / "metadata.json")
    assert metadata.stages[PipelineStage.EXTRACT_AUDIO].status == PipelineStageStatus.COMPLETED
    assert metadata.stages[PipelineStage.NORMALIZE_AUDIO].status == PipelineStageStatus.FAILED
    error = metadata.stages[PipelineStage.NORMALIZE_AUDIO].error
    assert error is not None
    assert error.code == "execution_failed"
    assert (artifact_dir / "audio_extracted.wav").exists()
    assert not (artifact_dir / "audio_normalized.wav").exists()


def test_process_does_not_execute_audio_prep_for_resume_only_report(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    write_resume_ready_metadata(media_path)
    media_processor = StubMediaProcessor()
    service = build_service(media_processor)

    plan = service.process(
        ProcessRequest(
            input_path=media_path,
            resume=True,
            only_report=True,
        )
    )

    assert media_processor.calls == []
    item = plan.items[0]
    assert (
        item.final_metadata.stages[PipelineStage.EXTRACT_AUDIO].status
        == PipelineStageStatus.COMPLETED
    )
    assert (
        item.final_metadata.stages[PipelineStage.NORMALIZE_AUDIO].status
        == PipelineStageStatus.COMPLETED
    )
