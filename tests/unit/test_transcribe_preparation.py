from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_report.application.transcribe.models import TranscribeRequest
from media_report.application.transcribe.preparation import TranscribeRunPreparer
from media_report.core.errors import ArtifactMetadataError, ResumeNotPossibleError
from media_report.domain.artifacts.entities import PipelineStage, PipelineStageStatus
from media_report.domain.artifacts.service import (
    ArtifactPlanner,
    ArtifactRootValidator,
    PipelineStatePlanner,
)
from media_report.domain.media.entities import MediaSource
from media_report.domain.transcription.entities import (
    TranscriptionResult,
    TranscriptionSegment,
)
from media_report.infrastructure.filesystem.metadata_repository import (
    JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner
from media_report.infrastructure.filesystem.transcription_repository import (
    JsonTranscriptionArtifactRepository,
)


def build_preparer() -> TranscribeRunPreparer:
    return TranscribeRunPreparer(
        scanner=FileSystemMediaScanner(),
        metadata_repository=JsonPipelineMetadataRepository(),
        artifact_planner=ArtifactPlanner(),
        artifact_validator=ArtifactRootValidator(),
        state_planner=PipelineStatePlanner(),
    )


def build_transcription_result() -> TranscriptionResult:
    return TranscriptionResult(
        provider="faster-whisper",
        model="small",
        requested_language="es",
        detected_language="es",
        segments=(
            TranscriptionSegment(
                index=0,
                start_seconds=0.0,
                end_seconds=1.0,
                text="hola mundo",
            ),
        ),
        duration_ms=120,
        device_preference="auto",
        effective_device="cpu",
    )


def write_completed_artifacts(media_path: Path, *, delete_source: bool = False) -> Path:
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(media_path)
    source = FileSystemMediaScanner().classify(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=source.kind),
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
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    artifact_plan.audio_normalized.write_text("normalized", encoding="utf-8")
    JsonTranscriptionArtifactRepository().write(
        result=build_transcription_result(),
        transcript_raw_path=artifact_plan.transcript_raw,
        transcript_segments_path=artifact_plan.transcript_segments,
    )
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.EXTRACT_AUDIO)
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.NORMALIZE_AUDIO)
    metadata = planner.record_transcription(metadata, result=build_transcription_result())
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.TRANSCRIBE)
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    if delete_source:
        media_path.unlink()
    return artifact_plan.root_dir


def write_extract_only_artifacts(media_path: Path, *, delete_source: bool = False) -> Path:
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(media_path)
    source = FileSystemMediaScanner().classify(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=source.kind),
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
    metadata = metadata.model_copy(
        update={
            "stages": {
                **metadata.stages,
                PipelineStage.EXTRACT_AUDIO: metadata.stages[
                    PipelineStage.EXTRACT_AUDIO
                ].model_copy(
                    update={
                        "status": PipelineStageStatus.COMPLETED,
                        "finished_at": metadata.generated_at,
                    }
                ),
            }
        }
    )
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    if delete_source:
        media_path.unlink()
    return artifact_plan.root_dir


def test_prepare_media_file_bootstraps_new_run(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")

    run = build_preparer().prepare(TranscribeRequest(input_path=media_path))

    assert run.source.path == media_path
    assert run.artifacts.root_dir.exists()
    assert run.metadata.artifacts.root_dir == run.artifacts.root_dir
    assert run.stage_decisions[0].stage == PipelineStage.EXTRACT_AUDIO


def test_prepare_artifact_root_reuses_completed_transcription_without_source(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_completed_artifacts(media_path, delete_source=True)

    run = build_preparer().prepare(TranscribeRequest(input_path=artifact_root))

    assert run.source.path == media_path
    assert not run.source.path.exists()
    assert run.metadata.stages[PipelineStage.TRANSCRIBE].status == PipelineStageStatus.COMPLETED
    assert any(
        decision.stage == PipelineStage.TRANSCRIBE and decision.decision.value == "reused"
        for decision in run.stage_decisions
    )


def test_prepare_existing_media_with_overwrite_reruns_only_transcribe(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    write_completed_artifacts(media_path)

    run = build_preparer().prepare(
        TranscribeRequest(
            input_path=media_path,
            overwrite=True,
        )
    )

    decisions = {decision.stage: decision.decision.value for decision in run.stage_decisions}
    assert decisions[PipelineStage.EXTRACT_AUDIO] == "reused"
    assert decisions[PipelineStage.NORMALIZE_AUDIO] == "reused"
    assert decisions[PipelineStage.TRANSCRIBE] == "planned"


def test_prepare_artifact_root_requires_source_when_repair_is_needed(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    artifact_root = write_extract_only_artifacts(media_path, delete_source=True)

    with pytest.raises(ResumeNotPossibleError):
        build_preparer().prepare(TranscribeRequest(input_path=artifact_root))


def test_prepare_artifact_root_fails_when_source_path_and_root_do_not_match(tmp_path: Path) -> None:
    media_path = tmp_path / "meeting.mp3"
    media_path.write_text("audio", encoding="utf-8")
    planner = ArtifactPlanner()
    source = FileSystemMediaScanner().classify(media_path)
    artifact_plan = planner.plan(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=source.kind),
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
    invalid_root = tmp_path / "wrong_media_report"
    invalid_root.mkdir()
    (invalid_root / "metadata.json").write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ArtifactMetadataError):
        build_preparer().prepare(TranscribeRequest(input_path=invalid_root))
