from __future__ import annotations

from media_report.application.reporting.execution import PromptRunExecutor
from media_report.application.reporting.models import RenderPromptRequest, RenderPromptResult
from media_report.application.reporting.preparation import PromptRunPreparer
from media_report.domain.artifacts.ports import PipelineMetadataRepository
from media_report.domain.artifacts.service import (
    ArtifactPlanner,
    ArtifactRootValidator,
    PipelineStatePlanner,
)
from media_report.domain.reporting.ports import PromptTemplateRepository
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


class PromptRenderService:
    def __init__(
        self,
        *,
        scanner: FileSystemMediaScanner,
        metadata_repository: PipelineMetadataRepository,
        template_repository: PromptTemplateRepository,
    ) -> None:
        artifact_planner = ArtifactPlanner()
        self._preparer = PromptRunPreparer(
            scanner=scanner,
            metadata_repository=metadata_repository,
            artifact_planner=artifact_planner,
            artifact_validator=ArtifactRootValidator(),
            state_planner=PipelineStatePlanner(),
        )
        self._executor = PromptRunExecutor(
            metadata_repository=metadata_repository,
            template_repository=template_repository,
            artifact_planner=artifact_planner,
        )

    def render_prompt(self, request: RenderPromptRequest) -> RenderPromptResult:
        prepared_run = self._preparer.prepare(request)
        final_metadata, prompt_path, prompt_text = self._executor.execute(prepared_run, request)
        return RenderPromptResult(
            source=prepared_run.source,
            artifacts=prepared_run.artifacts,
            stage_decisions=prepared_run.stage_decisions,
            final_metadata=final_metadata,
            prompt_path=prompt_path,
            rendered_prompt=prompt_text,
        )
