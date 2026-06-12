from __future__ import annotations

import json
from pathlib import Path

from media_report.application.process_media.models import ProcessRequest
from media_report.application.process_media.service import ProcessMediaService
from media_report.application.transcribe.models import TranscribeRequest, TranscribeResult
from media_report.domain.artifacts.entities import PipelineStage, PipelineStageStatus
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaSource
from media_report.infrastructure.filesystem.metadata_repository import (
  JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


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


class StubTemplateRepository:
  def get_template(self, name: str) -> str:
    return f"template:{name}"


class StubTranscribeService:
  def __init__(self) -> None:
    self.calls: list[TranscribeRequest] = []

  def transcribe(self, request: TranscribeRequest) -> TranscribeResult:
    self.calls.append(request)
    source = FileSystemMediaScanner().classify(request.input_path)
    planner = ArtifactPlanner()
    artifacts = planner.prepare_new(source.path)
    metadata = planner.bootstrap_metadata(
      source=source,
      artifact_plan=artifacts,
      template_name=request.workflow_template_name,
      llm_provider=request.workflow_llm_provider,
      llm_model=request.workflow_llm_model,
      output_format=request.workflow_output_format,
      language=request.language,
      selected_stages=request.workflow_selected_stages,
    )
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.EXTRACT_AUDIO)
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.NORMALIZE_AUDIO)
    metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.TRANSCRIBE)
    JsonPipelineMetadataRepository().write(metadata)
    return TranscribeResult(
      source=source,
      artifacts=artifacts,
      stage_decisions=(),
      final_metadata=metadata,
    )


def build_service(transcribe_service: StubTranscribeService) -> ProcessMediaService:
  return ProcessMediaService(
    scanner=FileSystemMediaScanner(),
    templates=StubTemplateRepository(),
    metadata_repository=JsonPipelineMetadataRepository(),
    transcribe_service=transcribe_service,
  )


def write_resume_ready_metadata(media_path: Path) -> Path:
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
    language=None,
    selected_stages=tuple(PipelineStage),
  )
  metadata = metadata.model_copy(
    update={
      "stages": {
        **metadata.stages,
        PipelineStage.EXTRACT_AUDIO: metadata.stages[PipelineStage.EXTRACT_AUDIO].model_copy(
          update={
            "status": PipelineStageStatus.COMPLETED,
            "finished_at": metadata.generated_at,
          }
        ),
        PipelineStage.NORMALIZE_AUDIO: metadata.stages[PipelineStage.NORMALIZE_AUDIO].model_copy(
          update={
            "status": PipelineStageStatus.COMPLETED,
            "finished_at": metadata.generated_at,
          }
        ),
        PipelineStage.TRANSCRIBE: metadata.stages[PipelineStage.TRANSCRIBE].model_copy(
          update={
            "status": PipelineStageStatus.COMPLETED,
            "finished_at": metadata.generated_at,
          }
        ),
      }
    }
  )
  JsonPipelineMetadataRepository().write(metadata)
  planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
  artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
  artifact_plan.audio_normalized.write_text("normalized", encoding="utf-8")
  artifact_plan.transcript_raw.write_text("transcript", encoding="utf-8")
  artifact_plan.transcript_segments.write_text(
    structured_transcript_payload(),
    encoding="utf-8",
  )
  return artifact_plan.root_dir


def test_process_delegates_default_flow_to_transcribe_service(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  transcribe_service = StubTranscribeService()
  service = build_service(transcribe_service)

  plan = service.process(ProcessRequest(input_path=media_path))

  assert len(transcribe_service.calls) == 1
  assert plan.items[0].final_metadata.stages[PipelineStage.TRANSCRIBE].status == (
    PipelineStageStatus.COMPLETED
  )


def test_process_only_transcribe_delegates_to_shared_use_case(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  transcribe_service = StubTranscribeService()
  service = build_service(transcribe_service)

  service.process(ProcessRequest(input_path=media_path, only_transcribe=True))

  request = transcribe_service.calls[0]
  assert request.workflow_selected_stages == (
    PipelineStage.EXTRACT_AUDIO,
    PipelineStage.NORMALIZE_AUDIO,
    PipelineStage.TRANSCRIBE,
  )


def test_process_only_report_does_not_delegate_to_transcribe_service(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  write_resume_ready_metadata(media_path)
  transcribe_service = StubTranscribeService()
  service = build_service(transcribe_service)

  plan = service.process(
    ProcessRequest(
      input_path=media_path,
      resume=True,
      only_report=True,
    )
  )

  assert transcribe_service.calls == []
  assert plan.items[0].final_metadata.stages[PipelineStage.TRANSCRIBE].status == (
    PipelineStageStatus.COMPLETED
  )
