from pathlib import Path

import pytest

from media_report.core.errors import ArtifactConflictError
from media_report.domain.artifacts.entities import (
    PipelineStage,
    PipelineStageStatus,
    StageErrorSummary,
)
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaKind, MediaSource


def test_prepare_creates_artifact_directory(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp4"
    media_path.write_text("x", encoding="utf-8")

    plan = ArtifactPlanner().prepare_new(media_path)

    assert plan.root_dir == tmp_path / "meeting_media_report"
    assert plan.root_dir.exists()
    assert plan.metadata_json.name == "metadata.json"


def test_prepare_blocks_existing_directory_without_overwrite(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp4"
    media_path.write_text("x", encoding="utf-8")
    existing = tmp_path / "meeting_media_report"
    existing.mkdir()

    with pytest.raises(ArtifactConflictError):
        ArtifactPlanner().prepare_new(media_path)


def test_bootstrap_metadata_contains_stage_plan(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("x", encoding="utf-8")
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(media_path)

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


def test_mark_stage_running_updates_stage_status(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("x", encoding="utf-8")
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=MediaKind.AUDIO),
        artifact_plan=artifact_plan,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language=None,
        selected_stages=tuple(PipelineStage),
    )

    updated = planner.mark_stage_running(metadata, stage=PipelineStage.EXTRACT_AUDIO)

    assert updated.stages[PipelineStage.EXTRACT_AUDIO].status == PipelineStageStatus.RUNNING
    assert updated.stages[PipelineStage.EXTRACT_AUDIO].started_at is not None
    assert updated.stages[PipelineStage.EXTRACT_AUDIO].finished_at is None
    assert updated.stages[PipelineStage.EXTRACT_AUDIO].resumable is False


def test_mark_stage_completed_clears_previous_error(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("x", encoding="utf-8")
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=MediaKind.AUDIO),
        artifact_plan=artifact_plan,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language=None,
        selected_stages=tuple(PipelineStage),
    )
    failed = planner.mark_stage_failed(
        metadata,
        stage=PipelineStage.EXTRACT_AUDIO,
        error=StageErrorSummary(
            type="MediaProcessingExecutionError",
            code="execution_failed",
            message="failed",
        ),
    )

    completed = planner.mark_stage_completed(failed, stage=PipelineStage.EXTRACT_AUDIO)

    assert completed.stages[PipelineStage.EXTRACT_AUDIO].status == PipelineStageStatus.COMPLETED
    assert completed.stages[PipelineStage.EXTRACT_AUDIO].error is None
    assert completed.stages[PipelineStage.EXTRACT_AUDIO].finished_at is not None
    assert completed.stages[PipelineStage.EXTRACT_AUDIO].resumable is True


def test_mark_stage_failed_records_error_summary(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("x", encoding="utf-8")
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=MediaKind.AUDIO),
        artifact_plan=artifact_plan,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language=None,
        selected_stages=tuple(PipelineStage),
    )

    failed = planner.mark_stage_failed(
        metadata,
        stage=PipelineStage.NORMALIZE_AUDIO,
        error=StageErrorSummary(
            type="MediaProcessingOutputError",
            code="output_missing",
            message="missing normalized output",
        ),
    )

    assert failed.stages[PipelineStage.NORMALIZE_AUDIO].status == PipelineStageStatus.FAILED
    error = failed.stages[PipelineStage.NORMALIZE_AUDIO].error
    assert error is not None
    assert error.code == "output_missing"
    assert failed.stages[PipelineStage.NORMALIZE_AUDIO].finished_at is not None
    assert failed.stages[PipelineStage.NORMALIZE_AUDIO].resumable is True
