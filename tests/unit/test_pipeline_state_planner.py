from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from media_report.core.errors import ArtifactMetadataError, StagePrerequisiteError
from media_report.domain.artifacts.entities import (
    PipelineStage,
    PipelineStageDecision,
    PipelineStageStatus,
)
from media_report.domain.artifacts.service import (
    ArtifactPlanner,
    ArtifactRootValidator,
    PipelineStatePlanner,
)
from media_report.domain.media.entities import MediaKind, MediaSource


def structured_transcript_payload(text: str = "transcript") -> str:
    return json.dumps(
        {
            "provider": "stub",
            "model": "stub-small",
            "requested_language": None,
            "detected_language": "en",
            "segments": [
                {
                    "index": 0,
                    "start_seconds": 0.0,
                    "end_seconds": 1.0,
                    "text": text,
                }
            ],
        }
    )


def build_metadata(tmp_path: Path):
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
    return media_path, artifact_plan, metadata


def test_plan_new_rejects_only_report_without_existing_artifacts() -> None:
    planner = PipelineStatePlanner()

    with pytest.raises(StagePrerequisiteError, match="Cannot start a fresh pipeline at 'report'"):
        planner.plan_new((PipelineStage.REPORT, PipelineStage.PDF))


def test_plan_resume_reuses_completed_stages_and_plans_tail(tmp_path: Path) -> None:
    _, artifact_plan, metadata = build_metadata(tmp_path)
    validator = ArtifactRootValidator()
    planner = PipelineStatePlanner()

    metadata = replace(
        metadata,
        stages={
            **metadata.stages,
            PipelineStage.EXTRACT_AUDIO: replace(
                metadata.stages[PipelineStage.EXTRACT_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
            PipelineStage.NORMALIZE_AUDIO: replace(
                metadata.stages[PipelineStage.NORMALIZE_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
            PipelineStage.TRANSCRIBE: replace(
                metadata.stages[PipelineStage.TRANSCRIBE],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
        },
    )
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    artifact_plan.audio_normalized.write_text("audio", encoding="utf-8")
    artifact_plan.transcript_raw.write_text("transcript", encoding="utf-8")
    artifact_plan.transcript_segments.write_text(
        structured_transcript_payload(),
        encoding="utf-8",
    )
    validator.validate(
        source=MediaSource(path=Path(metadata.source.path), kind=MediaKind.AUDIO),
        artifact_plan=artifact_plan,
        metadata=metadata,
    )

    decisions = planner.plan_resume(
        metadata=metadata,
        requested_stages=(PipelineStage.REPORT, PipelineStage.PDF),
    )

    assert decisions[0].decision == PipelineStageDecision.REUSED
    assert decisions[1].decision == PipelineStageDecision.REUSED
    assert decisions[2].decision == PipelineStageDecision.REUSED
    assert decisions[3].decision == PipelineStageDecision.PLANNED
    assert decisions[4].decision == PipelineStageDecision.PLANNED


def test_plan_resume_blocks_when_prerequisite_is_missing(tmp_path: Path) -> None:
    _, _, metadata = build_metadata(tmp_path)
    planner = PipelineStatePlanner()

    with pytest.raises(StagePrerequisiteError, match="prerequisite 'extract_audio'"):
        planner.plan_resume(
            metadata=metadata,
            requested_stages=(PipelineStage.REPORT, PipelineStage.PDF),
        )


def test_plan_resume_can_force_rerun_completed_stage(tmp_path: Path) -> None:
    _, artifact_plan, metadata = build_metadata(tmp_path)
    validator = ArtifactRootValidator()
    planner = PipelineStatePlanner()

    metadata = replace(
        metadata,
        stages={
            **metadata.stages,
            PipelineStage.EXTRACT_AUDIO: replace(
                metadata.stages[PipelineStage.EXTRACT_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
            PipelineStage.NORMALIZE_AUDIO: replace(
                metadata.stages[PipelineStage.NORMALIZE_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
            PipelineStage.TRANSCRIBE: replace(
                metadata.stages[PipelineStage.TRANSCRIBE],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
        },
    )
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    artifact_plan.audio_normalized.write_text("audio", encoding="utf-8")
    artifact_plan.transcript_raw.write_text("transcript", encoding="utf-8")
    artifact_plan.transcript_segments.write_text(
        structured_transcript_payload(),
        encoding="utf-8",
    )
    validator.validate(
        source=MediaSource(path=Path(metadata.source.path), kind=MediaKind.AUDIO),
        artifact_plan=artifact_plan,
        metadata=metadata,
    )

    decisions = planner.plan_resume(
        metadata=metadata,
        requested_stages=(
            PipelineStage.EXTRACT_AUDIO,
            PipelineStage.NORMALIZE_AUDIO,
            PipelineStage.TRANSCRIBE,
        ),
        force_stages={PipelineStage.TRANSCRIBE},
    )

    assert decisions[0].decision == PipelineStageDecision.REUSED
    assert decisions[1].decision == PipelineStageDecision.REUSED
    assert decisions[2].decision == PipelineStageDecision.PLANNED


def test_validator_rejects_completed_stage_without_outputs(tmp_path: Path) -> None:
    media_path, artifact_plan, metadata = build_metadata(tmp_path)
    validator = ArtifactRootValidator()

    metadata = replace(
        metadata,
        stages={
            **metadata.stages,
            PipelineStage.TRANSCRIBE: replace(
                metadata.stages[PipelineStage.TRANSCRIBE],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
        },
    )

    with pytest.raises(ArtifactMetadataError, match="required artifacts are missing"):
        validator.validate(
            source=MediaSource(path=media_path, kind=MediaKind.AUDIO),
            artifact_plan=artifact_plan,
            metadata=metadata,
        )


def test_validator_rejects_completed_transcription_with_legacy_segments_shape(
    tmp_path: Path,
) -> None:
    media_path, artifact_plan, metadata = build_metadata(tmp_path)
    validator = ArtifactRootValidator()

    metadata = replace(
        metadata,
        stages={
            **metadata.stages,
            PipelineStage.TRANSCRIBE: replace(
                metadata.stages[PipelineStage.TRANSCRIBE],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
        },
    )
    artifact_plan.transcript_raw.write_text("transcript", encoding="utf-8")
    artifact_plan.transcript_segments.write_text("[]", encoding="utf-8")

    with pytest.raises(ArtifactMetadataError, match="structured contract"):
        validator.validate(
            source=MediaSource(path=media_path, kind=MediaKind.AUDIO),
            artifact_plan=artifact_plan,
            metadata=metadata,
        )
