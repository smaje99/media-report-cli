from __future__ import annotations

from pathlib import Path

import pytest

from media_report.application.transcribe.execution import TranscribeRunExecutor
from media_report.application.transcribe.models import PreparedTranscribeRun, TranscribeRequest
from media_report.core.errors import MediaProcessingExecutionError, TranscriptionExecutionError
from media_report.domain.artifacts.entities import (
    PipelineStage,
    PipelineStageDecision,
    PipelineStageStatus,
    StageDecision,
)
from media_report.domain.artifacts.service import ArtifactPlanner, PipelineStatePlanner
from media_report.domain.media.entities import (
    ExtractAudioRequest,
    MediaProcessingResult,
    MediaSource,
    NormalizeAudioRequest,
)
from media_report.domain.transcription.entities import (
    TranscriptionRequest,
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


def build_transcription_result() -> TranscriptionResult:
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
                text="hola mundo",
            ),
        ),
        duration_ms=120,
        device_preference="auto",
        effective_device="cpu",
    )


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


class StubTranscriptionProvider:
    def __init__(
        self,
        *,
        result: TranscriptionResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or build_transcription_result()
        self.error = error
        self.calls: list[TranscriptionRequest] = []

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.result


def build_executor(
    media_processor: StubMediaProcessor,
    transcription_provider: StubTranscriptionProvider,
) -> TranscribeRunExecutor:
    return TranscribeRunExecutor(
        metadata_repository=JsonPipelineMetadataRepository(),
        media_processor=media_processor,
        transcription_provider=transcription_provider,
        transcription_artifact_repository=JsonTranscriptionArtifactRepository(),
        artifact_planner=ArtifactPlanner(),
    )


def build_new_run(media_path: Path) -> PreparedTranscribeRun:
    planner = ArtifactPlanner()
    source = FileSystemMediaScanner().classify(media_path)
    artifacts = planner.prepare_new(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=source.kind),
        artifact_plan=artifacts,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language="es",
        selected_stages=(
            PipelineStage.EXTRACT_AUDIO,
            PipelineStage.NORMALIZE_AUDIO,
            PipelineStage.TRANSCRIBE,
        ),
    )
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifacts.root_dir, metadata_schema_version=metadata.schema_version)
    return PreparedTranscribeRun(
        source=source,
        artifacts=artifacts,
        metadata=metadata,
        stage_decisions=PipelineStatePlanner().plan_new(
            (
                PipelineStage.EXTRACT_AUDIO,
                PipelineStage.NORMALIZE_AUDIO,
                PipelineStage.TRANSCRIBE,
            )
        ),
    )


def build_overwrite_run(media_path: Path) -> PreparedTranscribeRun:
    planner = ArtifactPlanner()
    source = FileSystemMediaScanner().classify(media_path)
    artifacts = planner.prepare_new(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=source.kind),
        artifact_plan=artifacts,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language="es",
        selected_stages=(
            PipelineStage.EXTRACT_AUDIO,
            PipelineStage.NORMALIZE_AUDIO,
            PipelineStage.TRANSCRIBE,
        ),
    )
    artifacts.audio_extracted.write_text("audio", encoding="utf-8")
    artifacts.audio_normalized.write_text("normalized", encoding="utf-8")
    JsonTranscriptionArtifactRepository().write(
        result=build_transcription_result(),
        transcript_raw_path=artifacts.transcript_raw,
        transcript_segments_path=artifacts.transcript_segments,
    )
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.EXTRACT_AUDIO)
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.NORMALIZE_AUDIO)
    metadata = planner.record_transcription(metadata, result=build_transcription_result())
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.TRANSCRIBE)
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifacts.root_dir, metadata_schema_version=metadata.schema_version)
    return PreparedTranscribeRun(
        source=source,
        artifacts=artifacts,
        metadata=metadata,
        stage_decisions=(
            stage_decision(PipelineStage.EXTRACT_AUDIO, PipelineStageDecision.REUSED),
            stage_decision(PipelineStage.NORMALIZE_AUDIO, PipelineStageDecision.REUSED),
            stage_decision(PipelineStage.TRANSCRIBE, PipelineStageDecision.PLANNED),
        ),
    )


def stage_decision(
    stage: PipelineStage,
    decision: PipelineStageDecision,
) -> StageDecision:
    return StageDecision(
        stage=stage,
        decision=decision,
        reason=f"{stage.value} is {decision.value}",
    )


def test_execute_planned_audio_and_transcribe_stages(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    media_processor = StubMediaProcessor()
    provider = StubTranscriptionProvider()

    metadata = build_executor(media_processor, provider).execute(
        build_new_run(media_path),
        TranscribeRequest(input_path=media_path),
    )

    assert media_processor.calls == ["extract_audio", "normalize_audio"]
    assert len(provider.calls) == 1
    assert metadata.stages[PipelineStage.TRANSCRIBE].status == PipelineStageStatus.COMPLETED


def test_execute_transcribe_stage_reuses_existing_audio(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    media_processor = StubMediaProcessor()
    provider = StubTranscriptionProvider()

    metadata = build_executor(media_processor, provider).execute(
        build_overwrite_run(media_path),
        TranscribeRequest(input_path=media_path, overwrite=True),
    )

    assert media_processor.calls == []
    assert len(provider.calls) == 1
    assert metadata.transcription is not None
    assert metadata.stages[PipelineStage.TRANSCRIBE].status == PipelineStageStatus.COMPLETED


def test_execute_marks_transcribe_failure_in_metadata_and_log(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    media_processor = StubMediaProcessor()
    provider = StubTranscriptionProvider(
        error=TranscriptionExecutionError(
            provider="faster-whisper",
            model="small",
            audio_path=str(media_path),
            detail="decoder crashed",
        )
    )
    run = build_new_run(media_path)

    with pytest.raises(TranscriptionExecutionError):
        build_executor(media_processor, provider).execute(
            run,
            TranscribeRequest(input_path=media_path),
        )

    metadata = JsonPipelineMetadataRepository().read(run.artifacts.metadata_json)
    transcribe_stage = metadata.stages[PipelineStage.TRANSCRIBE]
    assert transcribe_stage.status == PipelineStageStatus.FAILED
    assert transcribe_stage.error is not None
    assert transcribe_stage.error.code == "execution_failed"
    assert "transcribe: failed (execution_failed)" in run.artifacts.pipeline_log.read_text(
        encoding="utf-8"
    )


def test_execute_uses_typed_audio_error_mapping(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    media_processor = StubMediaProcessor(fail_normalize=True)
    provider = StubTranscriptionProvider()
    run = build_new_run(media_path)

    with pytest.raises(MediaProcessingExecutionError):
        build_executor(media_processor, provider).execute(
            run,
            TranscribeRequest(input_path=media_path),
        )

    metadata = JsonPipelineMetadataRepository().read(run.artifacts.metadata_json)
    normalize_stage = metadata.stages[PipelineStage.NORMALIZE_AUDIO]
    assert normalize_stage.status == PipelineStageStatus.FAILED
    assert normalize_stage.error is not None
    assert normalize_stage.error.code == "execution_failed"
