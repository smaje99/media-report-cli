from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from media_report.domain.artifacts.entities import ArtifactPlan, PipelineMetadata, StageDecision
from media_report.domain.media.entities import MediaSource


@dataclass(frozen=True)
class ProcessRequest:
    input_path: Path
    recursive: bool = False
    overwrite: bool = False
    resume: bool = False
    template_name: str = "generic"
    only_transcribe: bool = False
    only_report: bool = False
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1"
    language: str | None = None
    transcription_device: str = "auto"
    output_format: str = "pdf"


@dataclass(frozen=True)
class ProcessPlanItem:
    source: MediaSource
    artifacts: ArtifactPlan
    template_name: str
    stage_decisions: tuple[StageDecision, ...]
    final_metadata: PipelineMetadata


@dataclass(frozen=True)
class ProcessPlan:
    items: tuple[ProcessPlanItem, ...]
    remote_provider_selected: bool
