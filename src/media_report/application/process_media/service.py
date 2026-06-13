from __future__ import annotations

from pathlib import Path

from media_report.application.process_media.models import (
  ProcessPlan,
  ProcessPlanItem,
  ProcessRequest,
)
from media_report.application.reporting.models import GenerateReportRequest
from media_report.application.reporting.ports import ReportGenerationUseCase
from media_report.application.transcribe.models import TranscribeRequest
from media_report.application.transcribe.ports import TranscribeUseCase
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
  StageDecision,
)
from media_report.domain.artifacts.ports import PipelineMetadataRepository
from media_report.domain.artifacts.service import (
  ArtifactPlanner,
  ArtifactRootValidator,
  PipelineStatePlanner,
)
from media_report.domain.media.entities import MediaSource
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
    transcribe_service: TranscribeUseCase,
    report_service: ReportGenerationUseCase,
  ) -> None:
    self._scanner = scanner
    self._templates = templates
    self._metadata_repository = metadata_repository
    self._transcribe_service = transcribe_service
    self._report_service = report_service
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
    effective_resume = request.resume or request.overwrite
    items = tuple(
      self._process_source(
        source=source,
        request=request,
        selected_stages=selected_stages,
        effective_resume=effective_resume,
      )
      for source in sources
    )

    return ProcessPlan(
      items=items,
      remote_provider_selected=any(
        item.final_metadata.workflow.llm_provider != "ollama" for item in items
      ),
    )

  def _process_source(
    self,
    *,
    source: MediaSource,
    request: ProcessRequest,
    selected_stages: tuple[PipelineStage, ...],
    effective_resume: bool,
  ) -> ProcessPlanItem:
    if PipelineStage.TRANSCRIBE in selected_stages:
      return self._process_transcription_source(
        source=source,
        request=request,
        selected_stages=selected_stages,
        effective_resume=effective_resume,
      )
    if request.only_report and effective_resume:
      return self._process_report_source(
        source=source,
        request=request,
        selected_stages=selected_stages,
      )
    return self._plan_source_without_execution(
      source=source,
      request=request,
      selected_stages=selected_stages,
      effective_resume=effective_resume,
    )

  def _process_transcription_source(
    self,
    *,
    source: MediaSource,
    request: ProcessRequest,
    selected_stages: tuple[PipelineStage, ...],
    effective_resume: bool,
  ) -> ProcessPlanItem:
    transcribe_result = self._transcribe_service.transcribe(
      TranscribeRequest(
        input_path=source.path,
        overwrite=False,
        reuse_existing_artifacts=effective_resume,
        require_existing_artifacts_for_reuse=effective_resume,
        language=request.language,
        device_preference=request.transcription_device,
        workflow_template_name=request.template_name,
        workflow_llm_provider=request.llm_provider,
        workflow_llm_model=request.llm_model,
        workflow_output_format=request.output_format,
        workflow_selected_stages=selected_stages,
      )
    )
    return ProcessPlanItem(
      source=transcribe_result.source,
      artifacts=transcribe_result.artifacts,
      template_name=request.template_name,
      stage_decisions=transcribe_result.stage_decisions,
      final_metadata=transcribe_result.final_metadata,
    )

  def _process_report_source(
    self,
    *,
    source: MediaSource,
    request: ProcessRequest,
    selected_stages: tuple[PipelineStage, ...],
  ) -> ProcessPlanItem:
    artifact_root = self._resolve_report_artifact_root(source.path)
    report_result = self._report_service.generate_report(
      GenerateReportRequest(
        input_path=artifact_root,
        template_name=request.template_name,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        overwrite=request.overwrite,
        workflow_selected_stages=selected_stages,
      )
    )
    return ProcessPlanItem(
      source=report_result.source,
      artifacts=report_result.artifacts,
      template_name=report_result.final_metadata.workflow.template_name,
      stage_decisions=report_result.stage_decisions,
      final_metadata=report_result.final_metadata,
    )

  def _plan_source_without_execution(
    self,
    *,
    source: MediaSource,
    request: ProcessRequest,
    selected_stages: tuple[PipelineStage, ...],
    effective_resume: bool,
  ) -> ProcessPlanItem:
    artifacts = self._artifact_planner.plan(source.path)
    metadata, stage_decisions, artifacts = self._prepare_source_plan(
      source=source,
      artifacts=artifacts,
      request=request,
      selected_stages=selected_stages,
      effective_resume=effective_resume,
    )
    self._artifact_planner.append_stage_decisions(artifacts.root_dir, stage_decisions)
    return ProcessPlanItem(
      source=source,
      artifacts=artifacts,
      template_name=request.template_name,
      stage_decisions=stage_decisions,
      final_metadata=metadata,
    )

  def _prepare_source_plan(
    self,
    *,
    source: MediaSource,
    artifacts: ArtifactPlan,
    request: ProcessRequest,
    selected_stages: tuple[PipelineStage, ...],
    effective_resume: bool,
  ) -> tuple[PipelineMetadata, tuple[StageDecision, ...], ArtifactPlan]:
    if artifacts.root_dir.exists():
      return self._prepare_existing_source_plan(
        source=source,
        artifacts=artifacts,
        request=request,
        selected_stages=selected_stages,
        effective_resume=effective_resume,
      )
    return self._prepare_new_source_plan(
      source=source,
      request=request,
      selected_stages=selected_stages,
      effective_resume=effective_resume,
    )

  def _prepare_existing_source_plan(
    self,
    *,
    source: MediaSource,
    artifacts: ArtifactPlan,
    request: ProcessRequest,
    selected_stages: tuple[PipelineStage, ...],
    effective_resume: bool,
  ) -> tuple[PipelineMetadata, tuple[StageDecision, ...], ArtifactPlan]:
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
    return metadata, stage_decisions, artifacts

  def _prepare_new_source_plan(
    self,
    *,
    source: MediaSource,
    request: ProcessRequest,
    selected_stages: tuple[PipelineStage, ...],
    effective_resume: bool,
  ) -> tuple[PipelineMetadata, tuple[StageDecision, ...], ArtifactPlan]:
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
    return metadata, stage_decisions, artifacts

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

  def _resolve_report_artifact_root(self, media_path: Path) -> Path:
    artifact_root = self._artifact_planner.plan(media_path).root_dir
    if not artifact_root.exists():
      raise ResumeNotPossibleError(
        f"No existing artifact directory was found for '{media_path.name}'. "
        "Run without --resume to create bootstrap artifacts first."
      )
    return artifact_root
