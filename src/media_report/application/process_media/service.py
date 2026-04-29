from __future__ import annotations

from pathlib import Path

from media_report.application.process_media.models import (
    ProcessPlan,
    ProcessPlanItem,
    ProcessRequest,
)
from media_report.core.errors import InputPathError
from media_report.domain.artifacts.entities import PipelineStage
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaSource
from media_report.domain.reporting.ports import PromptTemplateRepository
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


class ProcessMediaService:
    def __init__(
        self,
        scanner: FileSystemMediaScanner,
        templates: PromptTemplateRepository,
    ) -> None:
        self._scanner = scanner
        self._templates = templates
        self._artifact_planner = ArtifactPlanner()

    def process(self, request: ProcessRequest) -> ProcessPlan:
        sources = self._discover_sources(request.input_path, recursive=request.recursive)
        if not sources:
            raise InputPathError("No supported audio or video files were found.")

        self._templates.get_template(request.template_name)

        items: list[ProcessPlanItem] = []
        for source in sources:
            artifacts = self._artifact_planner.prepare(source.path, overwrite=request.overwrite)
            metadata = self._artifact_planner.bootstrap_metadata(
                source=source,
                artifact_plan=artifacts,
                template_name=request.template_name,
                llm_provider=request.llm_provider,
                llm_model=request.llm_model,
                output_format=request.output_format,
            )
            self._artifact_planner.write_metadata(metadata)
            self._artifact_planner.initialize_log(artifacts.root_dir)

            items.append(
                ProcessPlanItem(
                    source=source,
                    artifacts=artifacts,
                    template_name=request.template_name,
                    stages=self._select_stages(request),
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

    @staticmethod
    def _select_stages(request: ProcessRequest) -> tuple[PipelineStage, ...]:
        if request.only_report:
            return (PipelineStage.REPORT, PipelineStage.PDF)
        if request.only_transcribe:
            return (
                PipelineStage.EXTRACT_AUDIO,
                PipelineStage.NORMALIZE_AUDIO,
                PipelineStage.TRANSCRIBE,
            )
        return (
            PipelineStage.EXTRACT_AUDIO,
            PipelineStage.NORMALIZE_AUDIO,
            PipelineStage.TRANSCRIBE,
            PipelineStage.REPORT,
            PipelineStage.PDF,
        )
