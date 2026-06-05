from __future__ import annotations

from collections.abc import Callable

from media_report.application.transcribe.models import PreparedTranscribeRun, TranscribeRequest
from media_report.core.errors import (
    FFmpegNotAvailableError,
    MediaProcessingError,
    MediaProcessingExecutionError,
    MediaProcessingOutputError,
    StagePrerequisiteError,
    TranscriptionExecutionError,
    TranscriptionModelError,
    TranscriptionOutputError,
    TranscriptionPersistenceError,
)
from media_report.domain.artifacts.entities import (
    ArtifactPlan,
    PipelineMetadata,
    PipelineStage,
    PipelineStageDecision,
    PipelineStageStatus,
    StageErrorSummary,
)
from media_report.domain.artifacts.ports import PipelineMetadataRepository
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import (
    ExtractAudioRequest,
    MediaProcessingResult,
    NormalizeAudioRequest,
)
from media_report.domain.media.ports import MediaProcessingService
from media_report.domain.transcription.entities import (
    TranscriptionRequest as ProviderTranscriptionRequest,
)
from media_report.domain.transcription.ports import (
    TranscriptionArtifactRepository,
    TranscriptionProvider,
)


class TranscribeRunExecutor:
    def __init__(
        self,
        *,
        metadata_repository: PipelineMetadataRepository,
        media_processor: MediaProcessingService,
        transcription_provider: TranscriptionProvider,
        transcription_artifact_repository: TranscriptionArtifactRepository,
        artifact_planner: ArtifactPlanner,
    ) -> None:
        self._metadata_repository = metadata_repository
        self._media_processor = media_processor
        self._transcription_provider = transcription_provider
        self._transcription_artifact_repository = transcription_artifact_repository
        self._artifact_planner = artifact_planner

    def execute(self, run: PreparedTranscribeRun, request: TranscribeRequest) -> PipelineMetadata:
        self._artifact_planner.append_stage_decisions(run.artifacts.root_dir, run.stage_decisions)

        metadata = self._execute_audio_stages(run=run)
        return self._execute_transcribe_stage(
            run=PreparedTranscribeRun(
                source=run.source,
                artifacts=run.artifacts,
                metadata=metadata,
                stage_decisions=run.stage_decisions,
            ),
            request=request,
        )

    def _execute_audio_stages(self, *, run: PreparedTranscribeRun) -> PipelineMetadata:
        decisions_by_stage = {decision.stage: decision for decision in run.stage_decisions}
        metadata = run.metadata

        extract_decision = decisions_by_stage[PipelineStage.EXTRACT_AUDIO].decision
        if extract_decision == PipelineStageDecision.PLANNED:
            metadata = self._execute_processing_stage(
                metadata=metadata,
                artifacts=run.artifacts,
                stage=PipelineStage.EXTRACT_AUDIO,
                action=lambda: self._media_processor.extract_audio(
                    ExtractAudioRequest(
                        source=run.source,
                        output_path=run.artifacts.audio_extracted,
                    )
                ),
            )

        normalize_decision = decisions_by_stage[PipelineStage.NORMALIZE_AUDIO].decision
        if normalize_decision == PipelineStageDecision.PLANNED:
            extract_status = metadata.stages[PipelineStage.EXTRACT_AUDIO].status
            if extract_status != PipelineStageStatus.COMPLETED:
                raise StagePrerequisiteError(
                    "Cannot execute 'normalize_audio' because 'extract_audio' did not complete."
                )
            metadata = self._execute_processing_stage(
                metadata=metadata,
                artifacts=run.artifacts,
                stage=PipelineStage.NORMALIZE_AUDIO,
                action=lambda: self._media_processor.normalize_audio(
                    NormalizeAudioRequest(
                        source_path=run.artifacts.audio_extracted,
                        output_path=run.artifacts.audio_normalized,
                    )
                ),
            )

        self._metadata_repository.write(metadata)
        return metadata

    def _execute_processing_stage(
        self,
        *,
        metadata: PipelineMetadata,
        artifacts: ArtifactPlan,
        stage: PipelineStage,
        action: Callable[[], MediaProcessingResult],
    ) -> PipelineMetadata:
        metadata = self._artifact_planner.mark_stage_running(metadata, stage=stage)
        self._metadata_repository.write(metadata)
        self._artifact_planner.append_log_event(artifacts.root_dir, f"{stage.value}: running")

        try:
            result = action()
        except Exception as exc:
            summary = _build_audio_stage_error_summary(exc)
            metadata = self._artifact_planner.mark_stage_failed(
                metadata,
                stage=stage,
                error=summary,
            )
            self._metadata_repository.write(metadata)
            self._artifact_planner.append_log_event(
                artifacts.root_dir,
                f"{stage.value}: failed ({summary.code}) - {summary.message}",
            )
            raise

        metadata = self._artifact_planner.mark_stage_completed(metadata, stage=stage)
        self._metadata_repository.write(metadata)
        self._artifact_planner.append_log_event(
            artifacts.root_dir,
            f"{stage.value}: completed - {result.output_path.name} ({result.duration_ms} ms)",
        )
        return metadata

    def _execute_transcribe_stage(
        self,
        *,
        run: PreparedTranscribeRun,
        request: TranscribeRequest,
    ) -> PipelineMetadata:
        transcribe_decision = next(
            decision
            for decision in run.stage_decisions
            if decision.stage == PipelineStage.TRANSCRIBE
        ).decision
        metadata = run.metadata
        if transcribe_decision != PipelineStageDecision.PLANNED:
            self._metadata_repository.write(metadata)
            return metadata

        if metadata.stages[PipelineStage.NORMALIZE_AUDIO].status != PipelineStageStatus.COMPLETED:
            raise StagePrerequisiteError(
                "Cannot execute 'transcribe' because 'normalize_audio' did not complete."
            )

        metadata = self._artifact_planner.mark_stage_running(
            metadata,
            stage=PipelineStage.TRANSCRIBE,
        )
        self._metadata_repository.write(metadata)
        self._artifact_planner.append_log_event(run.artifacts.root_dir, "transcribe: running")

        try:
            result = self._transcription_provider.transcribe(
                ProviderTranscriptionRequest(
                    audio_path=run.artifacts.audio_normalized,
                    requested_language=request.language,
                    model_override=request.transcription_model_override,
                    device_preference=request.device_preference,
                )
            )
            self._transcription_artifact_repository.write(
                result=result,
                transcript_raw_path=run.artifacts.transcript_raw,
                transcript_segments_path=run.artifacts.transcript_segments,
            )
        except Exception as exc:
            summary = _build_transcribe_stage_error_summary(exc)
            metadata = self._artifact_planner.mark_stage_failed(
                metadata,
                stage=PipelineStage.TRANSCRIBE,
                error=summary,
            )
            self._metadata_repository.write(metadata)
            self._artifact_planner.append_log_event(
                run.artifacts.root_dir,
                f"transcribe: failed ({summary.code}) - {summary.message}",
            )
            raise

        metadata = self._artifact_planner.record_transcription(metadata, result=result)
        metadata = self._artifact_planner.mark_stage_completed(
            metadata,
            stage=PipelineStage.TRANSCRIBE,
        )
        self._metadata_repository.write(metadata)
        fallback_suffix = (
            f" - {result.device_fallback_reason}" if result.device_fallback_reason else ""
        )
        self._artifact_planner.append_log_event(
            run.artifacts.root_dir,
            "transcribe: completed - "
            f"{result.provider}/{result.model} "
            f"device={result.effective_device} ({result.duration_ms} ms){fallback_suffix}",
        )
        return metadata


def _build_audio_stage_error_summary(error: Exception) -> StageErrorSummary:
    if isinstance(error, FFmpegNotAvailableError):
        code = "ffmpeg_not_available"
    elif isinstance(error, MediaProcessingExecutionError):
        code = "execution_failed"
    elif isinstance(error, MediaProcessingOutputError):
        code = "output_missing"
    elif isinstance(error, MediaProcessingError):
        code = "media_processing_failed"
    else:
        code = "media_processing_failed"
    return StageErrorSummary(
        type=error.__class__.__name__,
        code=code,
        message=str(error),
    )


def _build_transcribe_stage_error_summary(error: Exception) -> StageErrorSummary:
    if isinstance(error, TranscriptionModelError):
        code = "model_initialization_failed"
    elif isinstance(error, TranscriptionExecutionError):
        code = "execution_failed"
    elif isinstance(error, TranscriptionOutputError):
        code = "output_invalid"
    elif isinstance(error, TranscriptionPersistenceError):
        code = "artifact_write_failed"
    else:
        code = "transcription_failed"
    return StageErrorSummary(
        type=error.__class__.__name__,
        code=code,
        message=str(error),
    )
