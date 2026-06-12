from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class PipelineStage(StrEnum):
  EXTRACT_AUDIO = "extract_audio"
  NORMALIZE_AUDIO = "normalize_audio"
  TRANSCRIBE = "transcribe"
  REPORT = "report"
  PDF = "pdf"


class PipelineStageStatus(StrEnum):
  PLANNED = "planned"
  RUNNING = "running"
  COMPLETED = "completed"
  FAILED = "failed"
  SKIPPED = "skipped"


class PipelineStageDecision(StrEnum):
  PLANNED = "planned"
  REUSED = "reused"
  SKIPPED = "skipped"
  BLOCKED = "blocked"


class StageDecision(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  stage: PipelineStage
  decision: PipelineStageDecision
  reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ArtifactPlan(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  root_dir: Path
  metadata_json: Path
  pipeline_log: Path
  audio_extracted: Path
  audio_normalized: Path
  transcript_raw: Path
  transcript_segments: Path
  transcript_clean: Path
  prompt_used: Path
  llm_response_raw: Path
  report_markdown: Path
  report_pdf: Path


class StageErrorSummary(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PipelineStageMetadata(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  status: PipelineStageStatus
  resumable: bool
  started_at: str | None
  finished_at: str | None
  updated_at: str | None
  error: StageErrorSummary | None


class PipelineSourceMetadata(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  path: Path
  kind: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PipelineArtifactMetadata(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  root_dir: Path
  metadata_json: Path
  pipeline_log: Path
  audio_extracted: Path
  audio_normalized: Path
  transcript_raw: Path
  transcript_segments: Path
  transcript_clean: Path
  prompt_used: Path
  llm_response_raw: Path
  report_markdown: Path
  report_pdf: Path


class PipelineWorkflowMetadata(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  template_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  llm_provider: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  llm_model: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  output_format: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  language: str | None
  selected_stages: tuple[PipelineStage, ...]


class PipelineTranscriptionMetadata(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  provider: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  model: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  requested_language: str | None
  detected_language: str | None
  duration_ms: Annotated[int, Field(ge=0)]
  completed_at: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  device_preference: Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
  ] = "auto"
  effective_device: Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
  ] = "cpu"
  device_fallback_reason: str | None = None


class PipelineMetadata(BaseModel):
  model_config = ConfigDict(frozen=True, extra="forbid")

  schema_version: int
  generated_at: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
  source: PipelineSourceMetadata
  artifacts: PipelineArtifactMetadata
  workflow: PipelineWorkflowMetadata
  stages: dict[PipelineStage, PipelineStageMetadata]
  transcription: PipelineTranscriptionMetadata | None = None

  @model_validator(mode="after")
  def _validate_schema_version(self) -> PipelineMetadata:
    if self.schema_version != 2:
      raise ValueError(f"Unsupported metadata schema version: {self.schema_version}")
    return self
