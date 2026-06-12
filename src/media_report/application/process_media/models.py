from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from media_report.domain.artifacts.entities import ArtifactPlan, PipelineMetadata, StageDecision
from media_report.domain.media.entities import MediaSource


class ProcessRequest(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

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


class ProcessPlanItem(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  source: MediaSource
  artifacts: ArtifactPlan
  template_name: str
  stage_decisions: tuple[StageDecision, ...]
  final_metadata: PipelineMetadata


class ProcessPlan(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  items: tuple[ProcessPlanItem, ...]
  remote_provider_selected: bool
