from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from media_report.domain.artifacts.entities import ArtifactPlan, PipelineStage
from media_report.domain.media.entities import MediaSource


@dataclass(frozen=True)
class ProcessRequest:
    input_path: Path
    recursive: bool = False
    overwrite: bool = False
    template_name: str = "generic"
    only_transcribe: bool = False
    only_report: bool = False
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1"
    language: str | None = None
    output_format: str = "pdf"


@dataclass(frozen=True)
class ProcessPlanItem:
    source: MediaSource
    artifacts: ArtifactPlan
    template_name: str
    stages: tuple[PipelineStage, ...]


@dataclass(frozen=True)
class ProcessPlan:
    items: tuple[ProcessPlanItem, ...]
    remote_provider_selected: bool
