from __future__ import annotations

from pathlib import Path

from media_report.application.process_media.models import (
    ProcessPlan,
    ProcessPlanItem,
    ProcessRequest,
)
from media_report.core.errors import (
    ArtifactConflictError,
    ArtifactMetadataError,
    FFmpegNotAvailableError,
    InputPathError,
    MediaProcessingError,
    MediaProcessingExecutionError,
    MediaProcessingOutputError,
    ResumeNotPossibleError,
    StagePrerequisiteError,
)
from media_report.domain.artifacts.entities import (
    ArtifactPlan,
    PipelineMetadata,
    PipelineStage,
    PipelineStageDecision,
    PipelineStageStatus,
    StageDecision,
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
    MediaProcessingResult,
    MediaSource,
    NormalizeAudioRequest,
)
from media_report.domain.media.ports import MediaProcessingService
from media_report.domain.reporting.ports import PromptTemplateRepository
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


class ProcessMediaService:
    """
    A service for processing media files and generating report artifacts.
    """

    def __init__(
        self,
        scanner: FileSystemMediaScanner,
        templates: PromptTemplateRepository,
        metadata_repository: PipelineMetadataRepository,
        media_processor: MediaProcessingService,
    ) -> None:
        self._scanner = scanner
        self._templates = templates
        self._metadata_repository = metadata_repository
        self._media_processor = media_processor
        self._artifact_planner = ArtifactPlanner()
        self._artifact_validator = ArtifactRootValidator()
        self._state_planner = PipelineStatePlanner()

    def process(self, request: ProcessRequest) -> ProcessPlan:
        sources = self._discover_sources(request.input_path, recursive=request.recursive)
        if not sources:
            raise InputPathError("No supported audio or video files were found.")

        self._templates.get_template(request.template_name)
        selected_stages = self._state_planner.select_stages(
            only_transcribe=request.only_transcribe,
            only_report=request.only_report,
        )

        items: list[ProcessPlanItem] = []
        for source in sources:
            effective_resume = request.resume or request.overwrite
            artifacts = self._artifact_planner.plan(source.path)

            if artifacts.root_dir.exists():
                if not effective_resume:
                    raise ArtifactConflictError(
                        f"Artifact directory already exists for '{source.path.name}': "
                        f"{artifacts.root_dir}. Use --resume to reuse it. "
                        "--overwrite is still accepted as a deprecated alias."
                    )
                metadata = self._load_existing_metadata(source=source, artifacts=artifacts)
                metadata = self._artifact_planner.update_workflow(
                    metadata,
                    template_name=request.template_name,
                    llm_provider=request.llm_provider,
                    llm_model=request.llm_model,
                    output_format=request.output_format,
                    language=request.language,
                    selected_stages=selected_stages,
                )
                stage_decisions = self._state_planner.plan_resume(
                    metadata=metadata,
                    requested_stages=selected_stages,
                )
                self._metadata_repository.write(metadata)
                self._artifact_planner.ensure_log(artifacts.root_dir)
            else:
                if effective_resume:
                    raise ResumeNotPossibleError(
                        f"No existing artifact directory was found for '{source.path.name}'. "
                        "Run without --resume to create bootstrap artifacts first."
                    )
                stage_decisions = self._state_planner.plan_new(selected_stages)
                artifacts = self._artifact_planner.prepare_new(source.path)
                metadata = self._artifact_planner.bootstrap_metadata(
                    source=source,
                    artifact_plan=artifacts,
                    template_name=request.template_name,
                    llm_provider=request.llm_provider,
                    llm_model=request.llm_model,
                    output_format=request.output_format,
                    language=request.language,
                    selected_stages=selected_stages,
                )
                self._metadata_repository.write(metadata)
                self._artifact_planner.initialize_log(
                    artifacts.root_dir,
                    metadata_schema_version=metadata.schema_version,
                )

            self._artifact_planner.append_stage_decisions(artifacts.root_dir, stage_decisions)
            metadata = self._execute_audio_stages(
                source=source,
                artifacts=artifacts,
                metadata=metadata,
                stage_decisions=stage_decisions,
            )

            items.append(
                ProcessPlanItem(
                    source=source,
                    artifacts=artifacts,
                    template_name=request.template_name,
                    stage_decisions=stage_decisions,
                    final_metadata=metadata,
                )
            )

        return ProcessPlan(
            items=tuple(items),
            remote_provider_selected=request.llm_provider != "ollama",
        )

    def _discover_sources(self, path: Path, recursive: bool) -> list[MediaSource]:
        if not path.exists():
            raise InputPathError(f"Input path does not exist: {path}")
        if path.is_file():
            return [self._scanner.classify(path)]
        return self._scanner.scan(path, recursive=recursive)

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
        stage_decisions: tuple[StageDecision, ...],
    ) -> PipelineMetadata:
        decisions_by_stage = {decision.stage: decision for decision in stage_decisions}

        extract_decision = decisions_by_stage[PipelineStage.EXTRACT_AUDIO].decision
        if extract_decision == PipelineStageDecision.PLANNED:
            metadata = self._execute_stage(
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
            metadata = self._execute_stage(
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

    def _execute_stage(
        self,
        *,
        artifacts: ArtifactPlan,
        metadata: PipelineMetadata,
        stage: PipelineStage,
        action,
    ) -> PipelineMetadata:
        metadata = self._artifact_planner.mark_stage_running(metadata, stage=stage)
        self._metadata_repository.write(metadata)
        self._artifact_planner.append_log_event(
            artifacts.root_dir,
            f"{stage.value}: running",
        )

        try:
            result: MediaProcessingResult = action()
        except MediaProcessingError as exc:
            summary = self._build_stage_error_summary(exc)
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

    @staticmethod
    def _build_stage_error_summary(error: MediaProcessingError) -> StageErrorSummary:
        if isinstance(error, FFmpegNotAvailableError):
            code = "ffmpeg_not_available"
        elif isinstance(error, MediaProcessingExecutionError):
            code = "execution_failed"
        elif isinstance(error, MediaProcessingOutputError):
            code = "output_missing"
        else:
            code = "media_processing_failed"

        return StageErrorSummary(
            type=error.__class__.__name__,
            code=code,
            message=str(error),
        )
