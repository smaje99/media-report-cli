from __future__ import annotations

from pathlib import Path

from media_report.application.reporting.models import PreparedPromptRun, RenderPromptRequest
from media_report.core.errors import (
    PromptRenderOutputError,
    PromptRenderPersistenceError,
    PromptRenderPrerequisiteError,
    TemplateNotFoundError,
)
from media_report.domain.artifacts.entities import (
    PipelineMetadata,
    PipelineStage,
    StageErrorSummary,
)
from media_report.domain.artifacts.ports import PipelineMetadataRepository
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.reporting.ports import PromptTemplateRepository


class PromptRunExecutor:
    def __init__(
        self,
        *,
        metadata_repository: PipelineMetadataRepository,
        template_repository: PromptTemplateRepository,
        artifact_planner: ArtifactPlanner,
    ) -> None:
        self._metadata_repository = metadata_repository
        self._template_repository = template_repository
        self._artifact_planner = artifact_planner

    def execute(
        self,
        prepared_run: PreparedPromptRun,
        request: RenderPromptRequest,
    ) -> tuple[PipelineMetadata, Path, str]:
        del request
        report_decision = next(
            (
                decision
                for decision in prepared_run.stage_decisions
                if decision.stage == PipelineStage.REPORT
            ),
            None,
        )
        if report_decision is None:
            raise PromptRenderPrerequisiteError(
                "Prompt rendering could not resolve the report stage."
            )

        if report_decision.decision.value == "reused":
            prompt_text = prepared_run.artifacts.prompt_used.read_text(encoding="utf-8")
            return prepared_run.metadata, prepared_run.artifacts.prompt_used, prompt_text

        try:
            return self._render_and_persist_prompt(prepared_run)
        except TemplateNotFoundError as exc:
            wrapped = PromptRenderPrerequisiteError(str(exc))
            self._mark_failure(prepared_run.metadata, prepared_run.artifacts.root_dir, wrapped)
            raise wrapped from exc
        except OSError as exc:
            wrapped = PromptRenderPersistenceError(
                f"Could not persist prompt_used.md in '{prepared_run.artifacts.root_dir}'."
            )
            self._mark_failure(prepared_run.metadata, prepared_run.artifacts.root_dir, wrapped)
            raise wrapped from exc
        except (
            PromptRenderOutputError,
            PromptRenderPersistenceError,
            PromptRenderPrerequisiteError,
        ) as exc:
            self._mark_failure(prepared_run.metadata, prepared_run.artifacts.root_dir, exc)
            raise

    def _render_and_persist_prompt(
        self,
        prepared_run: PreparedPromptRun,
    ) -> tuple[PipelineMetadata, Path, str]:
        template_text = self._template_repository.get_template(
            prepared_run.metadata.workflow.template_name
        )
        transcript_text = prepared_run.artifacts.transcript_raw.read_text(
            encoding="utf-8"
        ).strip()
        if not transcript_text:
            raise PromptRenderPrerequisiteError(
                "Transcript is empty. Reporting requires a non-empty transcript_raw.txt."
            )
        prompt_text = build_prompt_document(
            metadata=prepared_run.metadata,
            source_name=prepared_run.source.path.name,
            source_kind=prepared_run.source.kind.value,
            artifact_root=prepared_run.artifacts.root_dir,
            template_text=template_text,
            transcript_text=transcript_text,
        )
        if not prompt_text.strip():
            raise PromptRenderOutputError("Rendered prompt is empty.")
        prepared_run.artifacts.prompt_used.write_text(prompt_text, encoding="utf-8")
        self._artifact_planner.append_log_event(
            prepared_run.artifacts.root_dir,
            "report prompt rendered "
            f"(template={prepared_run.metadata.workflow.template_name}, "
            f"chars={len(prompt_text)})",
        )
        return prepared_run.metadata, prepared_run.artifacts.prompt_used, prompt_text

    def _mark_failure(
        self,
        metadata: PipelineMetadata,
        artifact_root: Path,
        exc: Exception,
    ) -> PipelineMetadata:
        final_metadata = self._artifact_planner.mark_stage_failed(
            metadata,
            stage=PipelineStage.REPORT,
            error=StageErrorSummary(
                type=exc.__class__.__name__,
                code=_error_code(exc),
                message=str(exc),
            ),
        )
        self._metadata_repository.write(final_metadata)
        self._artifact_planner.append_log_event(
            artifact_root,
            f"report prompt render failed ({_error_code(exc)}): {exc}",
        )
        return final_metadata


def build_prompt_document(
    *,
    metadata: PipelineMetadata,
    source_name: str,
    source_kind: str,
    artifact_root: Path,
    template_text: str,
    transcript_text: str,
) -> str:
    transcription = metadata.transcription
    context_lines = [
        f"- Source Name: {source_name}",
        f"- Source Kind: {source_kind}",
        f"- Source Path: {metadata.source.path}",
        f"- Artifact Root: {artifact_root}",
        f"- Template: {metadata.workflow.template_name}",
        f"- Output Format: {metadata.workflow.output_format}",
        f"- Requested Language: {metadata.workflow.language or '<unset>'}",
    ]
    if transcription is not None:
        context_lines.extend(
            [
                f"- Transcription Provider: {transcription.provider}",
                f"- Transcription Model: {transcription.model}",
                f"- Detected Language: {transcription.detected_language or '<unset>'}",
            ]
        )

    return "\n".join(
        [
            f"# Prompt Template: {metadata.workflow.template_name}",
            "",
            "## Context",
            *context_lines,
            "",
            "## Template Instructions",
            template_text.strip(),
            "",
            "## Transcript",
            transcript_text,
            "",
        ]
    )


def _error_code(exc: Exception) -> str:
    if isinstance(exc, PromptRenderPrerequisiteError):
        return "prompt_render_prerequisite"
    if isinstance(exc, TemplateNotFoundError):
        return "prompt_template_not_found"
    if isinstance(exc, PromptRenderOutputError):
        return "prompt_render_output_invalid"
    if isinstance(exc, PromptRenderPersistenceError):
        return "prompt_render_persistence_failed"
    if isinstance(exc, OSError):
        return "prompt_render_persistence_failed"
    return "prompt_render_failed"
