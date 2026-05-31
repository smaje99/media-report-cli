import json
from dataclasses import replace
from pathlib import Path

import pytest

from media_report.core.errors import ArtifactMetadataError
from media_report.domain.artifacts.entities import (
    PipelineStage,
    PipelineStageStatus,
    PipelineTranscriptionMetadata,
)
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaKind, MediaSource
from media_report.infrastructure.filesystem.metadata_repository import (
    JsonPipelineMetadataRepository,
)


def test_metadata_repository_round_trip_v2(tmp_path: Path) -> None:
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
        selected_stages=(PipelineStage.REPORT, PipelineStage.PDF),
    )
    metadata = replace(
        metadata,
        transcription=PipelineTranscriptionMetadata(
            provider="stub",
            model="stub-small",
            requested_language="es",
            detected_language="es",
            duration_ms=123,
            completed_at=metadata.generated_at,
        ),
    )

    repository = JsonPipelineMetadataRepository()
    repository.write(metadata)

    loaded = repository.read(artifact_plan.metadata_json)

    assert loaded == metadata
    assert loaded.stages[PipelineStage.REPORT].status == PipelineStageStatus.PLANNED
    assert loaded.stages[PipelineStage.TRANSCRIBE].status == PipelineStageStatus.SKIPPED
    assert loaded.transcription is not None
    assert loaded.transcription.duration_ms == 123


def test_metadata_repository_rejects_non_v2_schema(tmp_path: Path) -> None:
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text('{"schema_version": 1}', encoding="utf-8")

    repository = JsonPipelineMetadataRepository()

    with pytest.raises(ArtifactMetadataError, match="Invalid artifact metadata"):
        repository.read(metadata_path)


def test_metadata_repository_reads_v2_payload_without_transcription_block(tmp_path: Path) -> None:
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
        selected_stages=(PipelineStage.REPORT, PipelineStage.PDF),
    )
    payload = metadata.to_payload()
    payload.pop("transcription")
    artifact_plan.metadata_json.write_text(json.dumps(payload), encoding="utf-8")

    repository = JsonPipelineMetadataRepository()
    loaded = repository.read(artifact_plan.metadata_json)

    assert loaded.transcription is None
    assert loaded.workflow.template_name == "generic"
