from pathlib import Path

import pytest

from media_report.core.errors import ArtifactConflictError
from media_report.domain.artifacts.entities import PipelineStage, PipelineStageStatus
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaKind, MediaSource


def test_prepare_creates_artifact_directory(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp4"
    media_path.write_text("x", encoding="utf-8")

    plan = ArtifactPlanner().prepare(media_path, overwrite=False)

    assert plan.root_dir == tmp_path / "meeting_media_report"
    assert plan.root_dir.exists()
    assert plan.metadata_json.name == "metadata.json"


def test_prepare_blocks_existing_directory_without_overwrite(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp4"
    media_path.write_text("x", encoding="utf-8")
    existing = tmp_path / "meeting_media_report"
    existing.mkdir()

    with pytest.raises(ArtifactConflictError):
        ArtifactPlanner().prepare(media_path, overwrite=False)


def test_bootstrap_metadata_contains_stage_plan(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("x", encoding="utf-8")
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare(media_path, overwrite=False)

    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=MediaKind.AUDIO),
        artifact_plan=artifact_plan,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language="es",
        selected_stages=(
            PipelineStage.EXTRACT_AUDIO,
            PipelineStage.NORMALIZE_AUDIO,
            PipelineStage.TRANSCRIBE,
        ),
    )

    assert metadata.schema_version == 2
    assert metadata.source.kind == "audio"
    assert metadata.workflow.language == "es"
    assert metadata.workflow.selected_stages == (
        PipelineStage.EXTRACT_AUDIO,
        PipelineStage.NORMALIZE_AUDIO,
        PipelineStage.TRANSCRIBE,
    )
    assert metadata.stages[PipelineStage.TRANSCRIBE].status == PipelineStageStatus.PLANNED
    assert metadata.stages[PipelineStage.REPORT].status == PipelineStageStatus.SKIPPED
    assert metadata.stages[PipelineStage.TRANSCRIBE].started_at is None
    assert metadata.stages[PipelineStage.TRANSCRIBE].finished_at is None
    assert metadata.stages[PipelineStage.TRANSCRIBE].updated_at == metadata.generated_at
    assert metadata.stages[PipelineStage.TRANSCRIBE].error is None
    assert metadata.stages[PipelineStage.REPORT].finished_at == metadata.generated_at
