from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from media_report.application.reporting.models import GenerateReportRequest, GenerateReportResult
from media_report.application.reporting.ports import PromptRenderUseCase
from media_report.core.errors import (
  LLMProviderConfigurationError,
  LLMProviderExecutionError,
  LLMProviderOutputError,
  PromptRenderPrerequisiteError,
  ReportArtifactPersistenceError,
)
from media_report.core.redaction import redact_text
from media_report.domain.artifacts.entities import (
  PipelineMetadata,
  PipelineStage,
  PipelineStageDecision,
  PipelineStageStatus,
  StageDecision,
  StageErrorSummary,
)
from media_report.domain.artifacts.ports import PipelineMetadataRepository
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.reporting.ports import LLMProvider

from .models import RenderPromptRequest


class ReportGenerationService:
  def __init__(
    self,
    *,
    prompt_renderer: PromptRenderUseCase,
    metadata_repository: PipelineMetadataRepository,
    provider_resolver: Callable[[str], LLMProvider],
    secret_values: Sequence[str] = (),
  ) -> None:
    self._prompt_renderer = prompt_renderer
    self._metadata_repository = metadata_repository
    self._provider_resolver = provider_resolver
    self._artifact_planner = ArtifactPlanner()
    self._secret_values = tuple(secret for secret in secret_values if secret)

  def generate_report(self, request: GenerateReportRequest) -> GenerateReportResult:
    prompt_result = self._prompt_renderer.render_prompt(
      RenderPromptRequest(
        input_path=request.input_path,
        template_name=request.template_name,
        overwrite=request.overwrite,
      )
    )
    metadata = self._update_effective_workflow(prompt_result.final_metadata, request=request)
    self._metadata_repository.write(metadata)

    report_decision = _report_stage_decision(prompt_result.stage_decisions)
    if (
      report_decision.decision == PipelineStageDecision.REUSED
      and metadata.stages[PipelineStage.REPORT].status == PipelineStageStatus.COMPLETED
      and not request.overwrite
    ):
      llm_response = prompt_result.artifacts.llm_response_raw.read_text(encoding="utf-8")
      report_text = prompt_result.artifacts.report_markdown.read_text(encoding="utf-8")
      return GenerateReportResult(
        source=prompt_result.source,
        artifacts=prompt_result.artifacts,
        stage_decisions=prompt_result.stage_decisions,
        final_metadata=metadata,
        prompt_path=prompt_result.prompt_path,
        response_path=prompt_result.artifacts.llm_response_raw,
        report_path=prompt_result.artifacts.report_markdown,
        rendered_prompt=prompt_result.rendered_prompt,
        llm_response=llm_response,
        report_text=report_text,
        remote_provider_selected=metadata.workflow.llm_provider != "ollama",
      )

    provider_name = metadata.workflow.llm_provider
    try:
      provider = self._provider_resolver(provider_name)
    except LLMProviderConfigurationError as exc:
      self._mark_failure(
        metadata=metadata,
        artifact_root=prompt_result.artifacts.root_dir,
        exc=exc,
      )
      raise exc.__class__(self._sanitize(str(exc))) from exc

    running_metadata = self._artifact_planner.mark_stage_running(
      metadata,
      stage=PipelineStage.REPORT,
    )
    self._metadata_repository.write(running_metadata)
    self._artifact_planner.append_log_event(
      prompt_result.artifacts.root_dir,
      "report generation started "
      f"(provider={provider_name}, model={metadata.workflow.llm_model})",
    )

    try:
      llm_response = provider.generate(
        prompt_result.rendered_prompt,
        model=metadata.workflow.llm_model,
      )
      if not llm_response.strip():
        raise LLMProviderOutputError("LLM provider returned empty output.")

      prompt_result.artifacts.llm_response_raw.write_text(llm_response, encoding="utf-8")
      report_text = _normalize_report_text(llm_response)
      prompt_result.artifacts.report_markdown.write_text(report_text, encoding="utf-8")
    except PromptRenderPrerequisiteError:
      raise
    except OSError as exc:
      wrapped = ReportArtifactPersistenceError(
        f"Could not persist report artifacts in '{prompt_result.artifacts.root_dir}'."
      )
      self._mark_failure(
        metadata=running_metadata,
        artifact_root=prompt_result.artifacts.root_dir,
        exc=wrapped,
      )
      raise wrapped from exc
    except (
      LLMProviderConfigurationError,
      LLMProviderExecutionError,
      LLMProviderOutputError,
    ) as exc:
      self._mark_failure(
        metadata=running_metadata,
        artifact_root=prompt_result.artifacts.root_dir,
        exc=exc,
      )
      raise exc.__class__(self._sanitize(str(exc))) from exc
    else:
      final_metadata = self._artifact_planner.mark_stage_completed(
        running_metadata,
        stage=PipelineStage.REPORT,
      )
      self._metadata_repository.write(final_metadata)
      self._artifact_planner.append_log_event(
        prompt_result.artifacts.root_dir,
        "report generated "
        f"(provider={provider_name}, model={metadata.workflow.llm_model}, "
        f"chars={len(report_text)})",
      )
      return GenerateReportResult(
        source=prompt_result.source,
        artifacts=prompt_result.artifacts,
        stage_decisions=prompt_result.stage_decisions,
        final_metadata=final_metadata,
        prompt_path=prompt_result.prompt_path,
        response_path=prompt_result.artifacts.llm_response_raw,
        report_path=prompt_result.artifacts.report_markdown,
        rendered_prompt=prompt_result.rendered_prompt,
        llm_response=llm_response,
        report_text=report_text,
        remote_provider_selected=provider_name != "ollama",
      )

  def _mark_failure(
    self,
    *,
    metadata: PipelineMetadata,
    artifact_root: Path,
    exc: Exception,
  ) -> PipelineMetadata:
    sanitized_message = self._sanitize(str(exc))
    final_metadata = self._artifact_planner.mark_stage_failed(
      metadata,
      stage=PipelineStage.REPORT,
      error=StageErrorSummary(
        type=exc.__class__.__name__,
        code=_error_code(exc),
        message=sanitized_message,
      ),
    )
    self._metadata_repository.write(final_metadata)
    self._artifact_planner.append_log_event(
      artifact_root,
      f"report generation failed ({_error_code(exc)}): {sanitized_message}",
    )
    return final_metadata

  def _sanitize(self, text: str) -> str:
    return redact_text(text, secrets=self._secret_values)

  def _update_effective_workflow(
    self,
    metadata: PipelineMetadata,
    *,
    request: GenerateReportRequest,
  ) -> PipelineMetadata:
    return self._artifact_planner.update_workflow(
      metadata,
      template_name=request.template_name or metadata.workflow.template_name,
      llm_provider=request.llm_provider or metadata.workflow.llm_provider,
      llm_model=request.llm_model or metadata.workflow.llm_model,
      output_format=metadata.workflow.output_format,
      language=metadata.workflow.language,
      selected_stages=metadata.workflow.selected_stages,
    )


def _normalize_report_text(text: str) -> str:
  return text if text.endswith("\n") else f"{text}\n"


def _report_stage_decision(stage_decisions: tuple[StageDecision, ...]) -> StageDecision:
  for decision in stage_decisions:
    if decision.stage == PipelineStage.REPORT:
      return decision
  raise PromptRenderPrerequisiteError("Report generation could not resolve the report stage.")


def _error_code(exc: Exception) -> str:
  if isinstance(exc, LLMProviderConfigurationError):
    return "llm_provider_configuration_invalid"
  if isinstance(exc, LLMProviderExecutionError):
    return "llm_provider_execution_failed"
  if isinstance(exc, LLMProviderOutputError):
    return "llm_provider_output_invalid"
  if isinstance(exc, ReportArtifactPersistenceError):
    return "report_artifact_persistence_failed"
  return "report_generation_failed"
