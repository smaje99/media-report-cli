from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from media_report.core.constants import ARTIFACT_SUFFIX
from media_report.core.errors import (
    ArtifactConflictError,
    ArtifactMetadataError,
    StagePrerequisiteError,
)
from media_report.domain.artifacts.entities import (
    ArtifactPlan,
    PipelineArtifactMetadata,
    PipelineMetadata,
    PipelineSourceMetadata,
    PipelineStage,
    PipelineStageDecision,
    PipelineStageMetadata,
    PipelineStageStatus,
    PipelineWorkflowMetadata,
    StageDecision,
    StageErrorSummary,
)
from media_report.domain.media.entities import MediaSource


class ArtifactPlanner:
    def plan(self, media_path: Path) -> ArtifactPlan:
        root_dir = media_path.parent / f"{media_path.stem}{ARTIFACT_SUFFIX}"
        return ArtifactPlan(
            root_dir=root_dir,
            metadata_json=root_dir / "metadata.json",
            pipeline_log=root_dir / "pipeline.log",
            audio_extracted=root_dir / "audio_extracted.wav",
            audio_normalized=root_dir / "audio_normalized.wav",
            transcript_raw=root_dir / "transcript_raw.txt",
            transcript_segments=root_dir / "transcript_segments.json",
            transcript_clean=root_dir / "transcript_clean.md",
            prompt_used=root_dir / "prompt_used.md",
            llm_response_raw=root_dir / "llm_response_raw.txt",
            report_markdown=root_dir / "report.md",
            report_pdf=root_dir / "report.pdf",
        )

    def prepare_new(self, media_path: Path) -> ArtifactPlan:
        artifact_plan = self.plan(media_path)
        if artifact_plan.root_dir.exists():
            raise ArtifactConflictError(
                f"Artifact directory already exists for '{media_path.name}': "
                f"{artifact_plan.root_dir}. Use --resume to reuse it. "
                "--overwrite is still accepted as a deprecated alias."
            )
        artifact_plan.root_dir.mkdir(parents=True, exist_ok=False)
        return artifact_plan

    def bootstrap_metadata(
        self,
        source: MediaSource,
        artifact_plan: ArtifactPlan,
        template_name: str,
        llm_provider: str,
        llm_model: str,
        output_format: str,
        language: str | None,
        selected_stages: tuple[PipelineStage, ...],
    ) -> PipelineMetadata:
        generated_at = datetime.now(UTC).isoformat()
        selected_stage_set = set(selected_stages)
        stages = {
            stage: self._build_stage_metadata(
                generated_at=generated_at,
                selected=stage in selected_stage_set,
            )
            for stage in PipelineStage
        }
        return PipelineMetadata(
            schema_version=2,
            generated_at=generated_at,
            source=PipelineSourceMetadata(
                path=str(source.path),
                kind=source.kind.value,
            ),
            artifacts=PipelineArtifactMetadata(
                root_dir=str(artifact_plan.root_dir),
                metadata_json=str(artifact_plan.metadata_json),
                pipeline_log=str(artifact_plan.pipeline_log),
                audio_extracted=str(artifact_plan.audio_extracted),
                audio_normalized=str(artifact_plan.audio_normalized),
                transcript_raw=str(artifact_plan.transcript_raw),
                transcript_segments=str(artifact_plan.transcript_segments),
                transcript_clean=str(artifact_plan.transcript_clean),
                prompt_used=str(artifact_plan.prompt_used),
                llm_response_raw=str(artifact_plan.llm_response_raw),
                report_markdown=str(artifact_plan.report_markdown),
                report_pdf=str(artifact_plan.report_pdf),
            ),
            workflow=self._build_workflow_metadata(
                template_name=template_name,
                llm_provider=llm_provider,
                llm_model=llm_model,
                output_format=output_format,
                language=language,
                selected_stages=selected_stages,
            ),
            stages=stages,
        )

    def update_workflow(
        self,
        metadata: PipelineMetadata,
        *,
        template_name: str,
        llm_provider: str,
        llm_model: str,
        output_format: str,
        language: str | None,
        selected_stages: tuple[PipelineStage, ...],
    ) -> PipelineMetadata:
        return replace(
            metadata,
            workflow=self._build_workflow_metadata(
                template_name=template_name,
                llm_provider=llm_provider,
                llm_model=llm_model,
                output_format=output_format,
                language=language,
                selected_stages=selected_stages,
            ),
        )

    def initialize_log(self, artifact_root: Path, *, metadata_schema_version: int) -> None:
        log_path = artifact_root / "pipeline.log"
        bootstrap_line = f"media-report metadata initialized (schema v{metadata_schema_version})\n"
        if not log_path.exists():
            log_path.write_text(bootstrap_line, encoding="utf-8")
            return
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(bootstrap_line)

    def ensure_log(self, artifact_root: Path) -> None:
        log_path = artifact_root / "pipeline.log"
        if log_path.exists():
            return
        log_path.write_text(
            "media-report pipeline log initialized for existing artifacts\n",
            encoding="utf-8",
        )

    def append_stage_decisions(
        self,
        artifact_root: Path,
        stage_decisions: tuple[StageDecision, ...],
    ) -> None:
        log_path = artifact_root / "pipeline.log"
        with log_path.open("a", encoding="utf-8") as handle:
            for decision in stage_decisions:
                handle.write(
                    f"{decision.stage.value}: {decision.decision.value} - {decision.reason}\n"
                )

    def append_log_event(self, artifact_root: Path, message: str) -> None:
        log_path = artifact_root / "pipeline.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{message}\n")

    def mark_stage_running(
        self,
        metadata: PipelineMetadata,
        *,
        stage: PipelineStage,
    ) -> PipelineMetadata:
        now = self._now()
        current = metadata.stages[stage]
        updated_stage = replace(
            current,
            status=PipelineStageStatus.RUNNING,
            resumable=False,
            started_at=now,
            finished_at=None,
            updated_at=now,
            error=None,
        )
        return replace(metadata, stages={**metadata.stages, stage: updated_stage})

    def mark_stage_completed(
        self,
        metadata: PipelineMetadata,
        *,
        stage: PipelineStage,
    ) -> PipelineMetadata:
        now = self._now()
        current = metadata.stages[stage]
        updated_stage = replace(
            current,
            status=PipelineStageStatus.COMPLETED,
            resumable=True,
            started_at=current.started_at or now,
            finished_at=now,
            updated_at=now,
            error=None,
        )
        return replace(metadata, stages={**metadata.stages, stage: updated_stage})

    def mark_stage_failed(
        self,
        metadata: PipelineMetadata,
        *,
        stage: PipelineStage,
        error: StageErrorSummary,
    ) -> PipelineMetadata:
        now = self._now()
        current = metadata.stages[stage]
        updated_stage = replace(
            current,
            status=PipelineStageStatus.FAILED,
            resumable=True,
            started_at=current.started_at or now,
            finished_at=now,
            updated_at=now,
            error=error,
        )
        return replace(metadata, stages={**metadata.stages, stage: updated_stage})

    @staticmethod
    def _build_workflow_metadata(
        *,
        template_name: str,
        llm_provider: str,
        llm_model: str,
        output_format: str,
        language: str | None,
        selected_stages: tuple[PipelineStage, ...],
    ) -> PipelineWorkflowMetadata:
        return PipelineWorkflowMetadata(
            template_name=template_name,
            llm_provider=llm_provider,
            llm_model=llm_model,
            output_format=output_format,
            language=language,
            selected_stages=selected_stages,
        )

    @staticmethod
    def _build_stage_metadata(*, generated_at: str, selected: bool) -> PipelineStageMetadata:
        if selected:
            return PipelineStageMetadata(
                status=PipelineStageStatus.PLANNED,
                resumable=True,
                started_at=None,
                finished_at=None,
                updated_at=generated_at,
                error=None,
            )
        return PipelineStageMetadata(
            status=PipelineStageStatus.SKIPPED,
            resumable=True,
            started_at=None,
            finished_at=generated_at,
            updated_at=generated_at,
            error=None,
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()


class ArtifactRootValidator:
    def validate(
        self,
        *,
        source: MediaSource,
        artifact_plan: ArtifactPlan,
        metadata: PipelineMetadata,
    ) -> None:
        expected_paths = {
            "root_dir": artifact_plan.root_dir,
            "metadata_json": artifact_plan.metadata_json,
            "pipeline_log": artifact_plan.pipeline_log,
            "audio_extracted": artifact_plan.audio_extracted,
            "audio_normalized": artifact_plan.audio_normalized,
            "transcript_raw": artifact_plan.transcript_raw,
            "transcript_segments": artifact_plan.transcript_segments,
            "transcript_clean": artifact_plan.transcript_clean,
            "prompt_used": artifact_plan.prompt_used,
            "llm_response_raw": artifact_plan.llm_response_raw,
            "report_markdown": artifact_plan.report_markdown,
            "report_pdf": artifact_plan.report_pdf,
        }

        if Path(metadata.source.path) != source.path:
            raise ArtifactMetadataError(
                f"Artifact metadata source path does not match '{source.path}'."
            )
        if metadata.source.kind != source.kind.value:
            raise ArtifactMetadataError(
                f"Artifact metadata kind does not match '{source.kind.value}' "
                f"for '{source.path.name}'."
            )

        artifact_metadata = metadata.artifacts.to_payload()
        for field_name, expected_path in expected_paths.items():
            persisted_path = Path(str(artifact_metadata[field_name]))
            if persisted_path != expected_path:
                raise ArtifactMetadataError(
                    f"Artifact metadata path mismatch for '{field_name}': "
                    f"expected '{expected_path}', "
                    f"found '{persisted_path}'."
                )

        for stage in PipelineStage:
            if metadata.stages[stage].status != PipelineStageStatus.COMPLETED:
                continue

            if missing_outputs := self.missing_outputs_for_stage(
                artifact_plan=artifact_plan,
                stage=stage,
            ):
                missing_names = ", ".join(path.name for path in missing_outputs)
                raise ArtifactMetadataError(
                    f"Stage '{stage.value}' is marked completed but "
                    "required artifacts are missing: "
                    f"{missing_names}."
                )

    @staticmethod
    def outputs_for_stage(
        *,
        artifact_plan: ArtifactPlan,
        stage: PipelineStage,
    ) -> tuple[Path, ...]:
        match stage:
            case PipelineStage.EXTRACT_AUDIO:
                return (artifact_plan.audio_extracted,)
            case PipelineStage.NORMALIZE_AUDIO:
                return (artifact_plan.audio_normalized,)
            case PipelineStage.TRANSCRIBE:
                return (artifact_plan.transcript_raw, artifact_plan.transcript_segments)
            case PipelineStage.REPORT:
                return (
                    artifact_plan.prompt_used,
                    artifact_plan.llm_response_raw,
                    artifact_plan.report_markdown,
                )
            case PipelineStage.PDF:
                return (artifact_plan.report_pdf,)

    def missing_outputs_for_stage(
        self,
        *,
        artifact_plan: ArtifactPlan,
        stage: PipelineStage,
    ) -> tuple[Path, ...]:
        return tuple(
            output_path
            for output_path in self.outputs_for_stage(artifact_plan=artifact_plan, stage=stage)
            if not output_path.exists()
        )


class PipelineStatePlanner:
    STAGE_SEQUENCE = tuple(PipelineStage)

    def select_stages(
        self,
        *,
        only_transcribe: bool,
        only_report: bool,
    ) -> tuple[PipelineStage, ...]:
        if only_transcribe and only_report:
            raise StagePrerequisiteError(
                "Choose either --only-transcribe or --only-report, not both."
            )
        if only_report:
            return (PipelineStage.REPORT, PipelineStage.PDF)
        if only_transcribe:
            return (
                PipelineStage.EXTRACT_AUDIO,
                PipelineStage.NORMALIZE_AUDIO,
                PipelineStage.TRANSCRIBE,
            )
        return self.STAGE_SEQUENCE

    def plan_new(self, requested_stages: tuple[PipelineStage, ...]) -> tuple[StageDecision, ...]:
        self._ensure_new_run_can_start(requested_stages)
        requested_stage_set = set(requested_stages)
        return tuple(
            StageDecision(
                stage=stage,
                decision=(
                    PipelineStageDecision.PLANNED
                    if stage in requested_stage_set
                    else PipelineStageDecision.SKIPPED
                ),
                reason=(
                    "Stage selected for this invocation."
                    if stage in requested_stage_set
                    else "Stage omitted from this invocation."
                ),
            )
            for stage in self.STAGE_SEQUENCE
        )

    def plan_resume(
        self,
        *,
        metadata: PipelineMetadata,
        requested_stages: tuple[PipelineStage, ...],
    ) -> tuple[StageDecision, ...]:
        furthest_requested_index = max(
            self.STAGE_SEQUENCE.index(stage) for stage in requested_stages
        )
        requested_stage_set = set(requested_stages)
        satisfied_stages: set[PipelineStage] = set()
        decisions: list[StageDecision] = []

        for index, stage in enumerate(self.STAGE_SEQUENCE):
            if index > furthest_requested_index:
                decisions.append(
                    StageDecision(
                        stage=stage,
                        decision=PipelineStageDecision.SKIPPED,
                        reason="Stage omitted from this invocation.",
                    )
                )
                continue

            stage_metadata = metadata.stages[stage]
            if stage_metadata.status == PipelineStageStatus.COMPLETED:
                decisions.append(
                    StageDecision(
                        stage=stage,
                        decision=PipelineStageDecision.REUSED,
                        reason="Using completed artifacts from existing metadata.",
                    )
                )
                satisfied_stages.add(stage)
                continue

            if stage in requested_stage_set:
                missing_prerequisite = self._first_missing_prerequisite(
                    stage=stage,
                    satisfied_stages=satisfied_stages,
                )
                if missing_prerequisite is not None:
                    raise StagePrerequisiteError(
                        f"Cannot plan '{stage.value}' because prerequisite "
                        f"'{missing_prerequisite.value}' is not completed "
                        "in the existing artifacts."
                    )
                decisions.append(
                    StageDecision(
                        stage=stage,
                        decision=PipelineStageDecision.PLANNED,
                        reason="Stage selected for this invocation.",
                    )
                )
                satisfied_stages.add(stage)
                continue

            blocking_stage = self._first_requested_stage_after(
                index=index,
                requested_stages=requested_stages,
            )
            if blocking_stage is None:
                decisions.append(
                    StageDecision(
                        stage=stage,
                        decision=PipelineStageDecision.SKIPPED,
                        reason="Stage omitted from this invocation.",
                    )
                )
                continue
            raise StagePrerequisiteError(
                f"Cannot plan '{blocking_stage.value}' because prerequisite '{stage.value}' "
                "is not completed. Resume after the earlier stages finish successfully."
            )

        return tuple(decisions)

    def _ensure_new_run_can_start(self, requested_stages: tuple[PipelineStage, ...]) -> None:
        first_requested_stage = requested_stages[0]
        if first_requested_stage == PipelineStage.EXTRACT_AUDIO:
            return
        raise StagePrerequisiteError(
            f"Cannot start a fresh pipeline at '{first_requested_stage.value}'. "
            "Create the earlier artifacts first, then rerun with --resume."
        )

    def _first_missing_prerequisite(
        self,
        *,
        stage: PipelineStage,
        satisfied_stages: set[PipelineStage],
    ) -> PipelineStage | None:
        stage_index = self.STAGE_SEQUENCE.index(stage)
        return next(
            (
                prior_stage
                for prior_stage in self.STAGE_SEQUENCE[:stage_index]
                if prior_stage not in satisfied_stages
            ),
            None,
        )

    def _first_requested_stage_after(
        self,
        *,
        index: int,
        requested_stages: tuple[PipelineStage, ...],
    ) -> PipelineStage | None:
        return next(
            (stage for stage in requested_stages if self.STAGE_SEQUENCE.index(stage) > index),
            None,
        )
