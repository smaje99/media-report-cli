from __future__ import annotations

from pathlib import Path

from media_report.application.process_media.models import (
  ProcessPlan,
  ProcessPlanItem,
  ProcessRequest,
)
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
  ) -> None:
    self._scanner = scanner
    self._templates = templates
    self._metadata_repository = metadata_repository
    self._transcribe_service = transcribe_service
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
      if PipelineStage.TRANSCRIBE in selected_stages:
        transcribe_result = self._transcribe_service.transcribe(
          TranscribeRequest(
            input_path=source.path,
            overwrite=False,
            reuse_existing_artifacts=request.resume or request.overwrite,
            require_existing_artifacts_for_reuse=request.resume or request.overwrite,
            language=request.language,
            device_preference=request.transcription_device,
            workflow_template_name=request.template_name,
            workflow_llm_provider=request.llm_provider,
            workflow_llm_model=request.llm_model,
            workflow_output_format=request.output_format,
            workflow_selected_stages=selected_stages,
          )
        )
        items.append(
          ProcessPlanItem(
            source=transcribe_result.source,
            artifacts=transcribe_result.artifacts,
            template_name=request.template_name,
            stage_decisions=transcribe_result.stage_decisions,
            final_metadata=transcribe_result.final_metadata,
          )
        )
        continue

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
