from __future__ import annotations

from pathlib import Path

from media_report.application.transcribe.models import (
    DEFAULT_TRANSCRIBE_STAGES,
    TranscribeRequest,
    TranscribeResult,
)
from media_report.core.errors import (
    ArtifactConflictError,
    ArtifactMetadataError,
    InputPathError,
    ResumeNotPossibleError,
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
from media_report.domain.artifacts.service import (
    ArtifactPlanner,
    ArtifactRootValidator,
    PipelineStatePlanner,
)
from media_report.domain.media.entities import (
    ExtractAudioRequest,
    MediaKind,
    MediaProcessingResult,
    MediaSource,
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
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


class TranscribeService:
    def __init__(
        self,
        *,
        scanner: FileSystemMediaScanner,
        metadata_repository: PipelineMetadataRepository,
        media_processor: MediaProcessingService,
        transcription_provider: TranscriptionProvider,
        transcription_artifact_repository: TranscriptionArtifactRepository,
    ) -> None:
        self._scanner = scanner
        self._metadata_repository = metadata_repository
        self._media_processor = media_processor
        self._transcription_provider = transcription_provider
        self._transcription_artifact_repository = transcription_artifact_repository
        self._artifact_planner = ArtifactPlanner()
        self._artifact_validator = ArtifactRootValidator()
        self._state_planner = PipelineStatePlanner()

    def transcribe(self, request: TranscribeRequest) -> TranscribeResult:
        source, artifacts, metadata, stage_decisions = self._prepare_run(request)
        self._artifact_planner.append_stage_decisions(artifacts.root_dir, stage_decisions)

        metadata = self._execute_audio_stages(
            source=source,
            artifacts=artifacts,
            metadata=metadata,
            stage_decisions=stage_decisions,
        )
        metadata = self._execute_transcribe_stage(
            artifacts=artifacts,
            metadata=metadata,
            stage_decisions=stage_decisions,
            request=request,
        )

        return TranscribeResult(
            source=source,
            artifacts=artifacts,
            stage_decisions=stage_decisions,
            final_metadata=metadata,
        )

    def _prepare_run(
        self,
        request: TranscribeRequest,
    ) -> tuple[MediaSource, ArtifactPlan, PipelineMetadata, tuple]:
        if request.input_path.is_file():
            return self._prepare_media_source_run(request)
        if request.input_path.is_dir():
            return self._prepare_artifact_root_run(request)
        raise InputPathError(f"Input path does not exist: {request.input_path}")

    def _prepare_media_source_run(
        self,
        request: TranscribeRequest,
    ) -> tuple[MediaSource, ArtifactPlan, PipelineMetadata, tuple]:
        source = self._scanner.classify(request.input_path)
        artifacts = self._artifact_planner.plan(source.path)
        selected_stages = request.workflow_selected_stages

        if artifacts.root_dir.exists():
            return self._prepare_existing_media_source_run(
                source=source,
                artifacts=artifacts,
                request=request,
                selected_stages=selected_stages,
            )

        if request.reuse_existing_artifacts and request.require_existing_artifacts_for_reuse:
            raise ResumeNotPossibleError(
                f"No existing artifact directory was found for '{source.path.name}'. "
                "Run without --resume to create bootstrap artifacts first."
            )

        stage_decisions = self._state_planner.plan_new(selected_stages)
        artifacts = self._artifact_planner.prepare_new(source.path)
        metadata = self._artifact_planner.bootstrap_metadata(
            source=source,
            artifact_plan=artifacts,
            template_name=request.workflow_template_name,
            llm_provider=request.workflow_llm_provider,
            llm_model=request.workflow_llm_model,
            output_format=request.workflow_output_format,
            language=request.language,
            selected_stages=selected_stages,
        )
        self._metadata_repository.write(metadata)
        self._artifact_planner.initialize_log(
            artifacts.root_dir,
            metadata_schema_version=metadata.schema_version,
        )
        return source, artifacts, metadata, stage_decisions

    def _prepare_existing_media_source_run(
        self,
        *,
        source: MediaSource,
        artifacts: ArtifactPlan,
        request: TranscribeRequest,
        selected_stages: tuple[PipelineStage, ...],
    ) -> tuple[MediaSource, ArtifactPlan, PipelineMetadata, tuple]:
        if not request.reuse_existing_artifacts:
            raise ArtifactConflictError(
                f"Artifact directory already exists for '{source.path.name}': "
                f"{artifacts.root_dir}. Use --resume to reuse it. "
                "--overwrite is still accepted as a deprecated alias."
            )

        metadata = self._load_existing_metadata(source=source, artifacts=artifacts)
        metadata = self._artifact_planner.update_workflow(
            metadata,
            template_name=request.workflow_template_name,
            llm_provider=request.workflow_llm_provider,
            llm_model=request.workflow_llm_model,
            output_format=request.workflow_output_format,
            language=request.language,
            selected_stages=selected_stages,
        )
        stage_decisions = self._state_planner.plan_resume(
            metadata=metadata,
            requested_stages=selected_stages,
            force_stages={PipelineStage.TRANSCRIBE} if request.overwrite else None,
        )
        self._metadata_repository.write(metadata)
        self._artifact_planner.ensure_log(artifacts.root_dir)
        return source, artifacts, metadata, stage_decisions

    def _prepare_artifact_root_run(
        self,
        request: TranscribeRequest,
    ) -> tuple[MediaSource, ArtifactPlan, PipelineMetadata, tuple]:
        metadata_path = request.input_path / "metadata.json"
        if not metadata_path.exists():
            raise ArtifactMetadataError(
                f"Artifact metadata is missing for '{request.input_path.name}': {metadata_path}."
            )

        metadata = self._metadata_repository.read(metadata_path)
        source = MediaSource(
            path=Path(metadata.source.path),
            kind=self._scanner.classify(Path(metadata.source.path)).kind
            if Path(metadata.source.path).exists()
            else MediaKind(metadata.source.kind),
        )
        artifacts = self._artifact_planner.plan(source.path)
        if artifacts.root_dir != request.input_path:
            raise ArtifactMetadataError(
                "Artifact root does not match metadata source path: "
                f"expected '{artifacts.root_dir}', found '{request.input_path}'."
            )

        self._artifact_validator.validate(
            source=source,
            artifact_plan=artifacts,
            metadata=metadata,
        )
        metadata = self._artifact_planner.update_workflow(
            metadata,
            template_name=request.workflow_template_name,
            llm_provider=request.workflow_llm_provider,
            llm_model=request.workflow_llm_model,
            output_format=request.workflow_output_format,
            language=request.language,
            selected_stages=request.workflow_selected_stages,
        )
        stage_decisions = self._state_planner.plan_resume(
            metadata=metadata,
            requested_stages=request.workflow_selected_stages,
            force_stages={PipelineStage.TRANSCRIBE} if request.overwrite else None,
        )
        if self._requires_source_repairs(stage_decisions) and not source.path.exists():
            raise ResumeNotPossibleError(
                "Original source media is required to repair prerequisites for "
                f"'{request.input_path.name}', but it is missing: {source.path}."
            )
        self._metadata_repository.write(metadata)
        self._artifact_planner.ensure_log(artifacts.root_dir)
        return source, artifacts, metadata, stage_decisions

    def _load_existing_metadata(
        self, *, source: MediaSource, artifacts: ArtifactPlan
    ) -> PipelineMetadata:
        try:
            metadata = self._metadata_repository.read(artifacts.metadata_json)
        except FileNotFoundError as exc:
            raise ArtifactMetadataError(
                f"Artifact metadata is missing for '{source.path.name}': {artifacts.metadata_json}."
            ) from exc
        self._artifact_validator.validate(
            source=source,
            artifact_plan=artifacts,
            metadata=metadata,
        )
        return metadata

    def _execute_audio_stages(
        self,
        *,
        source: MediaSource,
        artifacts: ArtifactPlan,
        metadata: PipelineMetadata,
        stage_decisions: tuple,
    ) -> PipelineMetadata:
        decisions_by_stage = {decision.stage: decision for decision in stage_decisions}

        extract_decision = decisions_by_stage[PipelineStage.EXTRACT_AUDIO].decision
        if extract_decision == PipelineStageDecision.PLANNED:
            metadata = self._execute_processing_stage(
                artifacts=artifacts,
                metadata=metadata,
                stage=PipelineStage.EXTRACT_AUDIO,
                action=lambda: self._media_processor.extract_audio(
                    ExtractAudioRequest(
                        source=source,
                        output_path=artifacts.audio_extracted,
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
                artifacts=artifacts,
                metadata=metadata,
                stage=PipelineStage.NORMALIZE_AUDIO,
                action=lambda: self._media_processor.normalize_audio(
                    NormalizeAudioRequest(
                        source_path=artifacts.audio_extracted,
                        output_path=artifacts.audio_normalized,
                    )
                ),
            )

        self._metadata_repository.write(metadata)
        return metadata

    def _execute_processing_stage(
        self,
        *,
        artifacts: ArtifactPlan,
        metadata: PipelineMetadata,
        stage: PipelineStage,
        action,
    ) -> PipelineMetadata:
        metadata = self._artifact_planner.mark_stage_running(metadata, stage=stage)
        self._metadata_repository.write(metadata)
        self._artifact_planner.append_log_event(artifacts.root_dir, f"{stage.value}: running")

        try:
            result: MediaProcessingResult = action()
        except Exception as exc:
            summary = self._build_audio_stage_error_summary(exc)
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
        artifacts: ArtifactPlan,
        metadata: PipelineMetadata,
        stage_decisions: tuple,
        request: TranscribeRequest,
    ) -> PipelineMetadata:
        transcribe_decision = next(
            decision for decision in stage_decisions if decision.stage == PipelineStage.TRANSCRIBE
        ).decision
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
        self._artifact_planner.append_log_event(artifacts.root_dir, "transcribe: running")

        try:
            result = self._transcription_provider.transcribe(
                ProviderTranscriptionRequest(
                    audio_path=artifacts.audio_normalized,
                    requested_language=request.language,
                    model_override=request.transcription_model_override,
                    device_preference=request.device_preference,
                )
            )
            self._transcription_artifact_repository.write(
                result=result,
                transcript_raw_path=artifacts.transcript_raw,
                transcript_segments_path=artifacts.transcript_segments,
            )
        except Exception as exc:
            summary = self._build_transcribe_stage_error_summary(exc)
            metadata = self._artifact_planner.mark_stage_failed(
                metadata,
                stage=PipelineStage.TRANSCRIBE,
                error=summary,
            )
            self._metadata_repository.write(metadata)
            self._artifact_planner.append_log_event(
                artifacts.root_dir,
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
            artifacts.root_dir,
            "transcribe: completed - "
            f"{result.provider}/{result.model} "
            f"device={result.effective_device} ({result.duration_ms} ms){fallback_suffix}",
        )
        return metadata

    @staticmethod
    def _requires_source_repairs(stage_decisions: tuple) -> bool:
        return any(
            decision.stage in DEFAULT_TRANSCRIBE_STAGES
            and decision.decision == PipelineStageDecision.PLANNED
            for decision in stage_decisions
        )

    @staticmethod
    def _build_audio_stage_error_summary(error: Exception) -> StageErrorSummary:
        error_type = error.__class__.__name__
        message = str(error)
        if error_type == "FFmpegNotAvailableError":
            code = "ffmpeg_not_available"
        elif error_type == "MediaProcessingExecutionError":
            code = "execution_failed"
        elif error_type == "MediaProcessingOutputError":
            code = "output_missing"
        else:
            code = "media_processing_failed"
        return StageErrorSummary(type=error_type, code=code, message=message)

    @staticmethod
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
