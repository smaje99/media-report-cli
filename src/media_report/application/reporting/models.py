from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from media_report.domain.artifacts.entities import (
    ArtifactPlan,
    PipelineMetadata,
    PipelineStage,
    StageDecision,
)
from media_report.domain.media.entities import MediaSource

DEFAULT_RENDER_PROMPT_STAGES = (PipelineStage.REPORT,)


@dataclass(frozen=True)
class RenderPromptRequest:
    input_path: Path
    template_name: str | None = None
    overwrite: bool = False
    workflow_selected_stages: tuple[PipelineStage, ...] = DEFAULT_RENDER_PROMPT_STAGES


@dataclass(frozen=True)
class RenderPromptResult:
    source: MediaSource
    artifacts: ArtifactPlan
    stage_decisions: tuple[StageDecision, ...]
    final_metadata: PipelineMetadata
    prompt_path: Path
    rendered_prompt: str


@dataclass(frozen=True)
class PreparedPromptRun:
    source: MediaSource
    artifacts: ArtifactPlan
    metadata: PipelineMetadata
    stage_decisions: tuple[StageDecision, ...]
