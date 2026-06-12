from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from media_report.domain.artifacts.entities import (
  ArtifactPlan,
  PipelineMetadata,
  PipelineStage,
  StageDecision,
)
from media_report.domain.media.entities import MediaSource

DEFAULT_TRANSCRIBE_STAGES = (
  PipelineStage.EXTRACT_AUDIO,
  PipelineStage.NORMALIZE_AUDIO,
  PipelineStage.TRANSCRIBE,
)


class TranscribeRequest(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  input_path: Path
  overwrite: bool = False
  reuse_existing_artifacts: bool = True
  require_existing_artifacts_for_reuse: bool = False
  language: str | None = None
  transcription_model_override: str | None = None
  device_preference: str = "auto"
  workflow_template_name: str = "generic"
  workflow_llm_provider: str = "ollama"
  workflow_llm_model: str = "llama3.1"
  workflow_output_format: str = "pdf"
  workflow_selected_stages: tuple[PipelineStage, ...] = DEFAULT_TRANSCRIBE_STAGES


class TranscribeResult(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  source: MediaSource
  artifacts: ArtifactPlan
  stage_decisions: tuple[StageDecision, ...]
  final_metadata: PipelineMetadata


class PreparedTranscribeRun(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  source: MediaSource
  artifacts: ArtifactPlan
  metadata: PipelineMetadata
  stage_decisions: tuple[StageDecision, ...]
