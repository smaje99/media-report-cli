from __future__ import annotations

from pathlib import Path

import pytest

from media_report.application.transcribe.models import TranscribeRequest
from media_report.application.transcribe.service import TranscribeService
from media_report.core.errors import TranscriptionExecutionError
from media_report.domain.artifacts.entities import PipelineStage, PipelineStageStatus
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import (
    ExtractAudioRequest,
    MediaProcessingResult,
    MediaSource,
    NormalizeAudioRequest,
)
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


def build_transcription_result(
    *,
    device_preference: str = "auto",
    effective_device: str = "cpu",
    fallback_reason: str | None = None,
) -> TranscriptionResult:
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
        device_preference=device_preference,
        effective_device=effective_device,
        device_fallback_reason=fallback_reason,
    )


class StubMediaProcessor:
    def __init__(self) -> None:
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
        self.calls: list[object] = []

    def transcribe(self, request) -> TranscriptionResult:  # type: ignore[no-untyped-def]
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.result


def build_service(
    media_processor: StubMediaProcessor,
    transcription_provider: StubTranscriptionProvider,
) -> TranscribeService:
    return TranscribeService(
        scanner=FileSystemMediaScanner(),
        metadata_repository=JsonPipelineMetadataRepository(),
        media_processor=media_processor,
        transcription_provider=transcription_provider,
        transcription_artifact_repository=JsonTranscriptionArtifactRepository(),
    )


def write_completed_artifacts(
    media_path: Path,
    *,
    delete_source: bool = False,
) -> Path:
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
        selected_stages=(
            PipelineStage.EXTRACT_AUDIO,
            PipelineStage.NORMALIZE_AUDIO,
            PipelineStage.TRANSCRIBE,
        ),
    )
    result = build_transcription_result()
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    artifact_plan.audio_normalized.write_text("normalized", encoding="utf-8")
    JsonTranscriptionArtifactRepository().write(
        result=result,
        transcript_raw_path=artifact_plan.transcript_raw,
        transcript_segments_path=artifact_plan.transcript_segments,
    )
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.EXTRACT_AUDIO)
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.NORMALIZE_AUDIO)
    metadata = planner.record_transcription(metadata, result=result)
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.TRANSCRIBE)
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    if delete_source:
        media_path.unlink()
    return artifact_plan.root_dir


def write_extract_only_artifacts(media_path: Path) -> Path:
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
        selected_stages=(
            PipelineStage.EXTRACT_AUDIO,
            PipelineStage.NORMALIZE_AUDIO,
            PipelineStage.TRANSCRIBE,
        ),
    )
    metadata = metadata.model_copy(
        update={
            "stages": {
                **metadata.stages,
                PipelineStage.EXTRACT_AUDIO: metadata.stages[
                    PipelineStage.EXTRACT_AUDIO
                ].model_copy(
                    update={
                        "status": PipelineStageStatus.COMPLETED,
                        "finished_at": metadata.generated_at,
                    }
                ),
            }
        }
    )
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    return artifact_plan.root_dir


def test_transcribe_service_creates_artifacts_and_persists_transcription(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    media_processor = StubMediaProcessor()
    provider = StubTranscriptionProvider(
        result=build_transcription_result(
            effective_device="cuda",
            fallback_reason=None,
        )
    )
    service = build_service(media_processor, provider)

    result = service.transcribe(
        TranscribeRequest(
            input_path=media_path,
            device_preference="auto",
        )
    )

    assert media_processor.calls == ["extract_audio", "normalize_audio"]
    assert len(provider.calls) == 1
    assert result.artifacts.transcript_raw.exists()
    assert result.artifacts.transcript_segments.exists()
    assert result.final_metadata.stages[PipelineStage.TRANSCRIBE].status == (
        PipelineStageStatus.COMPLETED
    )
    assert result.final_metadata.transcription is not None
    assert result.final_metadata.transcription.effective_device == "cuda"


def test_transcribe_service_reuses_completed_artifacts_from_artifact_root(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_completed_artifacts(media_path, delete_source=True)
    media_processor = StubMediaProcessor()
    provider = StubTranscriptionProvider()
    service = build_service(media_processor, provider)

    result = service.transcribe(TranscribeRequest(input_path=artifact_root))

    assert media_processor.calls == []
    assert provider.calls == []
    assert result.final_metadata.stages[PipelineStage.TRANSCRIBE].status == (
        PipelineStageStatus.COMPLETED
    )


def test_transcribe_service_repairs_missing_normalized_audio(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_extract_only_artifacts(media_path)
    media_processor = StubMediaProcessor()
    provider = StubTranscriptionProvider()
    service = build_service(media_processor, provider)

    result = service.transcribe(TranscribeRequest(input_path=artifact_root))

    assert media_processor.calls == ["normalize_audio"]
    assert len(provider.calls) == 1
    assert result.final_metadata.stages[PipelineStage.NORMALIZE_AUDIO].status == (
        PipelineStageStatus.COMPLETED
    )
    assert result.final_metadata.stages[PipelineStage.TRANSCRIBE].status == (
        PipelineStageStatus.COMPLETED
    )


def test_transcribe_service_overwrite_reruns_only_transcribe(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    write_completed_artifacts(media_path)
    media_processor = StubMediaProcessor()
    provider = StubTranscriptionProvider(
        result=build_transcription_result(
            effective_device="cpu",
            fallback_reason="auto fallback to 'cpu' after cuda: unavailable",
        )
    )
    service = build_service(media_processor, provider)

    result = service.transcribe(
        TranscribeRequest(
            input_path=media_path,
            overwrite=True,
        )
    )

    assert media_processor.calls == []
    assert len(provider.calls) == 1
    assert result.final_metadata.transcription is not None
    assert result.final_metadata.transcription.device_fallback_reason is not None


def test_transcribe_service_marks_stage_failed_when_provider_fails(tmp_path: Path) -> None:
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
    service = build_service(media_processor, provider)

    with pytest.raises(TranscriptionExecutionError):
        service.transcribe(TranscribeRequest(input_path=media_path))

    artifact_root = media_path.parent / f"{media_path.stem}_media_report"
    metadata = JsonPipelineMetadataRepository().read(artifact_root / "metadata.json")
    transcribe_stage = metadata.stages[PipelineStage.TRANSCRIBE]
    assert transcribe_stage.status == PipelineStageStatus.FAILED
    assert transcribe_stage.error is not None
    assert transcribe_stage.error.code == "execution_failed"
