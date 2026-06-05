from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from media_report.application.reporting.models import PreparedPromptRun, RenderPromptRequest
from media_report.core.errors import (
    ArtifactMetadataError,
    InputPathError,
    PromptRenderPrerequisiteError,
    StagePrerequisiteError,
)
from media_report.domain.artifacts.entities import (
    PipelineMetadata,
    PipelineStage,
    PipelineStageMetadata,
    PipelineStageStatus,
)
from media_report.domain.artifacts.ports import PipelineMetadataRepository
from media_report.domain.artifacts.service import (
    ArtifactPlanner,
    ArtifactRootValidator,
    PipelineStatePlanner,
)
from media_report.domain.media.entities import MediaKind, MediaSource
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


class PromptRunPreparer:
    def __init__(
        self,
        *,
        scanner: FileSystemMediaScanner,
        metadata_repository: PipelineMetadataRepository,
        artifact_planner: ArtifactPlanner,
        artifact_validator: ArtifactRootValidator,
        state_planner: PipelineStatePlanner,
    ) -> None:
        self._scanner = scanner
        self._metadata_repository = metadata_repository
        self._artifact_planner = artifact_planner
        self._artifact_validator = artifact_validator
        self._state_planner = state_planner

    def prepare(self, request: RenderPromptRequest) -> PreparedPromptRun:
        if not request.input_path.exists():
            raise InputPathError(f"Input path does not exist: {request.input_path}")
        if not request.input_path.is_dir():
            raise PromptRenderPrerequisiteError(
                "Prompt rendering requires an existing artifact directory, not a media file."
            )

        metadata_path = request.input_path / "metadata.json"
        if not metadata_path.exists():
            raise PromptRenderPrerequisiteError(
                f"Artifact metadata is missing for '{request.input_path.name}': {metadata_path}."
            )

        try:
            metadata = self._metadata_repository.read(metadata_path)
        except ArtifactMetadataError as exc:
            raise PromptRenderPrerequisiteError(str(exc)) from exc

        source = self._resolve_source(metadata)
        artifacts = self._artifact_planner.plan(source.path)
        if artifacts.root_dir != request.input_path:
            raise PromptRenderPrerequisiteError(
                "Artifact root does not match metadata source path: "
                f"expected '{artifacts.root_dir}', found '{request.input_path}'."
            )

        try:
            self._artifact_validator.validate(
                source=source,
                artifact_plan=artifacts,
                metadata=metadata,
            )
        except ArtifactMetadataError as exc:
            raise PromptRenderPrerequisiteError(str(exc)) from exc

        effective_template = request.template_name or metadata.workflow.template_name
        metadata = self._artifact_planner.update_workflow(
            metadata,
            template_name=effective_template,
            llm_provider=metadata.workflow.llm_provider,
            llm_model=metadata.workflow.llm_model,
            output_format=metadata.workflow.output_format,
            language=metadata.workflow.language,
            selected_stages=request.workflow_selected_stages,
        )

        try:
            stage_decisions = self._state_planner.plan_resume(
                metadata=metadata,
                requested_stages=request.workflow_selected_stages,
                force_stages={PipelineStage.REPORT} if request.overwrite else None,
            )
        except StagePrerequisiteError as exc:
            raise PromptRenderPrerequisiteError(str(exc)) from exc

        if request.overwrite:
            metadata = _reset_report_stage_to_planned(metadata)

        self._metadata_repository.write(metadata)
        self._artifact_planner.ensure_log(artifacts.root_dir)
        return PreparedPromptRun(
            source=source,
            artifacts=artifacts,
            metadata=metadata,
            stage_decisions=stage_decisions,
        )

    def _resolve_source(self, metadata: PipelineMetadata) -> MediaSource:
        source_path = Path(metadata.source.path)
        if source_path.exists():
            return self._scanner.classify(source_path)
        return MediaSource(path=source_path, kind=MediaKind(metadata.source.kind))


def _reset_report_stage_to_planned(metadata: PipelineMetadata) -> PipelineMetadata:
    current = metadata.stages[PipelineStage.REPORT]
    planned_stage = PipelineStageMetadata(
        status=PipelineStageStatus.PLANNED,
        resumable=True,
        started_at=None,
        finished_at=None,
        updated_at=current.updated_at,
        error=None,
    )
    return replace(
        metadata,
        stages={**metadata.stages, PipelineStage.REPORT: planned_stage},
    )
