from __future__ import annotations

from pathlib import Path

from media_report.application.transcribe.models import (
  DEFAULT_TRANSCRIBE_STAGES,
  PreparedTranscribeRun,
  TranscribeRequest,
)
from media_report.core.errors import (
  ArtifactConflictError,
  ArtifactMetadataError,
  InputPathError,
  ResumeNotPossibleError,
)
from media_report.domain.artifacts.entities import (
  ArtifactPlan,
  PipelineMetadata,
  PipelineStage,
  PipelineStageDecision,
  StageDecision,
)
from media_report.domain.artifacts.ports import PipelineMetadataRepository
from media_report.domain.artifacts.service import (
  ArtifactPlanner,
  ArtifactRootValidator,
  PipelineStatePlanner,
)
from media_report.domain.media.entities import MediaKind, MediaSource
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


class TranscribeRunPreparer:
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

  def prepare(self, request: TranscribeRequest) -> PreparedTranscribeRun:
    if request.input_path.is_file():
      return self._prepare_media_source_run(request)
    if request.input_path.is_dir():
      return self._prepare_artifact_root_run(request)
    raise InputPathError(f"Input path does not exist: {request.input_path}")

  def _prepare_media_source_run(self, request: TranscribeRequest) -> PreparedTranscribeRun:
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
    return PreparedTranscribeRun(
      source=source,
      artifacts=artifacts,
      metadata=metadata,
      stage_decisions=stage_decisions,
    )

  def _prepare_existing_media_source_run(
    self,
    *,
    source: MediaSource,
    artifacts: ArtifactPlan,
    request: TranscribeRequest,
    selected_stages: tuple[PipelineStage, ...],
  ) -> PreparedTranscribeRun:
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
    return self._finalize_prepared_run(
      metadata=metadata,
      artifacts=artifacts,
      source=source,
      stage_decisions=stage_decisions,
    )

  def _prepare_artifact_root_run(self, request: TranscribeRequest) -> PreparedTranscribeRun:
    metadata_path = request.input_path / "metadata.json"
    if not metadata_path.exists():
      raise ArtifactMetadataError(
        f"Artifact metadata is missing for '{request.input_path.name}': {metadata_path}."
      )

    metadata = self._metadata_repository.read(metadata_path)
    source_path = Path(metadata.source.path)
    source = MediaSource(
      path=source_path,
      kind=(
        self._scanner.classify(source_path).kind
        if source_path.exists()
        else MediaKind(metadata.source.kind)
      ),
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
    if _requires_source_repairs(stage_decisions) and not source.path.exists():
      raise ResumeNotPossibleError(
        "Original source media is required to repair prerequisites for "
        f"'{request.input_path.name}', but it is missing: {source.path}."
      )
    return self._finalize_prepared_run(
      metadata=metadata,
      artifacts=artifacts,
      source=source,
      stage_decisions=stage_decisions,
    )

  def _finalize_prepared_run(
    self,
    *,
    metadata: PipelineMetadata,
    artifacts: ArtifactPlan,
    source: MediaSource,
    stage_decisions: tuple[StageDecision, ...],
  ) -> PreparedTranscribeRun:
    self._metadata_repository.write(metadata)
    self._artifact_planner.ensure_log(artifacts.root_dir)
    return PreparedTranscribeRun(
      source=source,
      artifacts=artifacts,
      metadata=metadata,
      stage_decisions=stage_decisions,
    )

  def _load_existing_metadata(
    self,
    *,
    source: MediaSource,
    artifacts: ArtifactPlan,
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


def _requires_source_repairs(stage_decisions: tuple[StageDecision, ...]) -> bool:
  return any(
    decision.stage in DEFAULT_TRANSCRIBE_STAGES
    and decision.decision == PipelineStageDecision.PLANNED
    for decision in stage_decisions
  )
