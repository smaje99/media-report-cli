from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


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


@dataclass(frozen=True)
class StageDecision:
    stage: PipelineStage
    decision: PipelineStageDecision
    reason: str


@dataclass(frozen=True)
class ArtifactPlan:
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


@dataclass(frozen=True)
class StageErrorSummary:
    type: str
    code: str
    message: str

    def to_payload(self) -> dict[str, str]:
        return {
            "type": self.type,
            "code": self.code,
            "message": self.message,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> StageErrorSummary:
        return cls(
            type=str(payload["type"]),
            code=str(payload["code"]),
            message=str(payload["message"]),
        )


@dataclass(frozen=True)
class PipelineStageMetadata:
    status: PipelineStageStatus
    resumable: bool
    started_at: str | None
    finished_at: str | None
    updated_at: str | None
    error: StageErrorSummary | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "resumable": self.resumable,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "updated_at": self.updated_at,
            "error": self.error.to_payload() if self.error else None,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PipelineStageMetadata:
        error_payload = payload.get("error")
        return cls(
            status=PipelineStageStatus(payload["status"]),
            resumable=bool(payload["resumable"]),
            started_at=payload.get("started_at"),
            finished_at=payload.get("finished_at"),
            updated_at=payload.get("updated_at"),
            error=StageErrorSummary.from_payload(error_payload) if error_payload else None,
        )


@dataclass(frozen=True)
class PipelineSourceMetadata:
    path: str
    kind: str

    def to_payload(self) -> dict[str, str]:
        return {
            "path": self.path,
            "kind": self.kind,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PipelineSourceMetadata:
        return cls(
            path=str(payload["path"]),
            kind=str(payload["kind"]),
        )


@dataclass(frozen=True)
class PipelineArtifactMetadata:
    root_dir: str
    metadata_json: str
    pipeline_log: str
    audio_extracted: str
    audio_normalized: str
    transcript_raw: str
    transcript_segments: str
    transcript_clean: str
    prompt_used: str
    llm_response_raw: str
    report_markdown: str
    report_pdf: str

    def to_payload(self) -> dict[str, str]:
        return {
            "root_dir": self.root_dir,
            "metadata_json": self.metadata_json,
            "pipeline_log": self.pipeline_log,
            "audio_extracted": self.audio_extracted,
            "audio_normalized": self.audio_normalized,
            "transcript_raw": self.transcript_raw,
            "transcript_segments": self.transcript_segments,
            "transcript_clean": self.transcript_clean,
            "prompt_used": self.prompt_used,
            "llm_response_raw": self.llm_response_raw,
            "report_markdown": self.report_markdown,
            "report_pdf": self.report_pdf,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PipelineArtifactMetadata:
        return cls(
            root_dir=str(payload["root_dir"]),
            metadata_json=str(payload["metadata_json"]),
            pipeline_log=str(payload["pipeline_log"]),
            audio_extracted=str(payload["audio_extracted"]),
            audio_normalized=str(payload["audio_normalized"]),
            transcript_raw=str(payload["transcript_raw"]),
            transcript_segments=str(payload["transcript_segments"]),
            transcript_clean=str(payload["transcript_clean"]),
            prompt_used=str(payload["prompt_used"]),
            llm_response_raw=str(payload["llm_response_raw"]),
            report_markdown=str(payload["report_markdown"]),
            report_pdf=str(payload["report_pdf"]),
        )


@dataclass(frozen=True)
class PipelineWorkflowMetadata:
    template_name: str
    llm_provider: str
    llm_model: str
    output_format: str
    language: str | None
    selected_stages: tuple[PipelineStage, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "template_name": self.template_name,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "output_format": self.output_format,
            "language": self.language,
            "selected_stages": [stage.value for stage in self.selected_stages],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PipelineWorkflowMetadata:
        return cls(
            template_name=str(payload["template_name"]),
            llm_provider=str(payload["llm_provider"]),
            llm_model=str(payload["llm_model"]),
            output_format=str(payload["output_format"]),
            language=payload.get("language"),
            selected_stages=tuple(PipelineStage(stage) for stage in payload["selected_stages"]),
        )


@dataclass(frozen=True)
class PipelineTranscriptionMetadata:
    provider: str
    model: str
    requested_language: str | None
    detected_language: str | None
    duration_ms: int
    completed_at: str
    device_preference: str = "auto"
    effective_device: str = "cpu"
    device_fallback_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "requested_language": self.requested_language,
            "detected_language": self.detected_language,
            "duration_ms": self.duration_ms,
            "completed_at": self.completed_at,
            "device_preference": self.device_preference,
            "effective_device": self.effective_device,
            "device_fallback_reason": self.device_fallback_reason,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PipelineTranscriptionMetadata:
        return cls(
            provider=str(payload["provider"]),
            model=str(payload["model"]),
            requested_language=payload.get("requested_language"),
            detected_language=payload.get("detected_language"),
            duration_ms=int(payload["duration_ms"]),
            completed_at=str(payload["completed_at"]),
            device_preference=str(payload.get("device_preference", "auto")),
            effective_device=str(payload.get("effective_device", "cpu")),
            device_fallback_reason=payload.get("device_fallback_reason"),
        )


@dataclass(frozen=True)
class PipelineMetadata:
    schema_version: int
    generated_at: str
    source: PipelineSourceMetadata
    artifacts: PipelineArtifactMetadata
    workflow: PipelineWorkflowMetadata
    stages: dict[PipelineStage, PipelineStageMetadata]
    transcription: PipelineTranscriptionMetadata | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "source": self.source.to_payload(),
            "artifacts": self.artifacts.to_payload(),
            "workflow": self.workflow.to_payload(),
            "stages": {
                stage.value: metadata.to_payload()
                for stage, metadata in self.stages.items()
            },
            "transcription": self.transcription.to_payload() if self.transcription else None,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PipelineMetadata:
        schema_version = int(payload["schema_version"])
        if schema_version != 2:
            raise ValueError(f"Unsupported metadata schema version: {schema_version}")

        return cls(
            schema_version=schema_version,
            generated_at=str(payload["generated_at"]),
            source=PipelineSourceMetadata.from_payload(payload["source"]),
            artifacts=PipelineArtifactMetadata.from_payload(payload["artifacts"]),
            workflow=PipelineWorkflowMetadata.from_payload(payload["workflow"]),
            stages={
                PipelineStage(stage): PipelineStageMetadata.from_payload(metadata)
                for stage, metadata in payload["stages"].items()
            },
            transcription=(
                PipelineTranscriptionMetadata.from_payload(payload["transcription"])
                if payload.get("transcription")
                else None
            ),
        )
