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

DEFAULT_RENDER_PROMPT_STAGES = (PipelineStage.REPORT,)


class RenderPromptRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_path: Path
    template_name: str | None = None
    overwrite: bool = False
    workflow_selected_stages: tuple[PipelineStage, ...] = DEFAULT_RENDER_PROMPT_STAGES


class RenderPromptResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: MediaSource
    artifacts: ArtifactPlan
    stage_decisions: tuple[StageDecision, ...]
    final_metadata: PipelineMetadata
    prompt_path: Path
    rendered_prompt: str


class PreparedPromptRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: MediaSource
    artifacts: ArtifactPlan
    metadata: PipelineMetadata
    stage_decisions: tuple[StageDecision, ...]
