from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_report.application.reporting import (
  GenerateReportRequest,
  PromptRenderService,
  ReportGenerationService,
)
from media_report.core.errors import LLMProviderExecutionError
from media_report.domain.artifacts.entities import PipelineStage, PipelineStageStatus
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaSource
from media_report.domain.reporting.ports import LLMProvider, PromptTemplateRepository
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


class StubTemplateRepository(PromptTemplateRepository):
  def get_template(self, name: str) -> str:
    return f"# Template {name}\n\nWrite a concise Markdown report."


class StubLLMProvider(LLMProvider):
  def __init__(self, response: str = "# Report\n\n- item", error: Exception | None = None) -> None:
    self.response = response
    self.error = error
    self.calls: list[tuple[str, str]] = []

  def generate(self, prompt: str, *, model: str) -> str:
    self.calls.append((prompt, model))
    if self.error is not None:
      raise self.error
    return self.response


def build_transcription_result(text: str = "hola mundo") -> TranscriptionResult:
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
        text=text,
      ),
    ),
    duration_ms=120,
    device_preference="auto",
    effective_device="cpu",
  )


def write_transcribed_artifact_root(media_path: Path, transcript_text: str = "hola mundo") -> Path:
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
    selected_stages=tuple(PipelineStage),
  )
  artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
  artifact_plan.audio_normalized.write_text("normalized", encoding="utf-8")
  JsonTranscriptionArtifactRepository().write(
    result=build_transcription_result(text=transcript_text),
    transcript_raw_path=artifact_plan.transcript_raw,
    transcript_segments_path=artifact_plan.transcript_segments,
  )
  metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.EXTRACT_AUDIO)
  metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.NORMALIZE_AUDIO)
  metadata = planner.record_transcription(
    metadata,
    result=build_transcription_result(text=transcript_text),
  )
  metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.TRANSCRIBE)
  JsonPipelineMetadataRepository().write(metadata)
  planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
  return artifact_plan.root_dir


def build_service(
  *,
  provider: LLMProvider,
  secret_values: tuple[str, ...] = (),
) -> ReportGenerationService:
  metadata_repository = JsonPipelineMetadataRepository()
  prompt_renderer = PromptRenderService(
    scanner=FileSystemMediaScanner(),
    metadata_repository=metadata_repository,
    template_repository=StubTemplateRepository(),
  )
  return ReportGenerationService(
    prompt_renderer=prompt_renderer,
    metadata_repository=metadata_repository,
    provider_resolver=lambda _provider_name: provider,
    secret_values=secret_values,
  )


def test_generate_report_persists_response_and_report_markdown(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  artifact_root = write_transcribed_artifact_root(media_path)
  provider = StubLLMProvider(response="# Report\n\n- item")

  result = build_service(provider=provider).generate_report(
    GenerateReportRequest(input_path=artifact_root)
  )

  assert provider.calls
  assert result.response_path.read_text(encoding="utf-8") == "# Report\n\n- item"
  assert result.report_path.read_text(encoding="utf-8") == "# Report\n\n- item\n"
  assert result.final_metadata.stages[PipelineStage.REPORT].status == PipelineStageStatus.COMPLETED
  assert result.remote_provider_selected is False


def test_generate_report_marks_stage_failed_and_redacts_secrets(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  artifact_root = write_transcribed_artifact_root(media_path)
  provider = StubLLMProvider(
    error=LLMProviderExecutionError("Bearer sk-example-secret request failed")
  )

  service = build_service(provider=provider, secret_values=("sk-example-secret",))

  with pytest.raises(LLMProviderExecutionError) as exc_info:
    service.generate_report(
      GenerateReportRequest(
        input_path=artifact_root,
        llm_provider="openai-compatible",
        llm_model="gpt-4.1-mini",
      )
    )

  message = str(exc_info.value)
  metadata_payload = json.loads((artifact_root / "metadata.json").read_text(encoding="utf-8"))
  assert "sk-example-secret" not in message
  assert "sk-example-secret" not in metadata_payload["stages"]["report"]["error"]["message"]
  assert metadata_payload["stages"]["report"]["status"] == "failed"


def test_generate_report_overwrite_regenerates_existing_report(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  artifact_root = write_transcribed_artifact_root(media_path)
  initial_provider = StubLLMProvider(response="# Initial")
  overwrite_provider = StubLLMProvider(response="# Updated")

  build_service(provider=initial_provider).generate_report(
    GenerateReportRequest(input_path=artifact_root)
  )
  result = build_service(provider=overwrite_provider).generate_report(
    GenerateReportRequest(input_path=artifact_root, overwrite=True)
  )

  assert result.response_path.read_text(encoding="utf-8") == "# Updated"
  assert result.report_path.read_text(encoding="utf-8") == "# Updated\n"
  assert overwrite_provider.calls


def test_generate_report_updates_effective_provider_and_model(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  artifact_root = write_transcribed_artifact_root(media_path)
  provider = StubLLMProvider(response="# Remote")

  result = build_service(provider=provider).generate_report(
    GenerateReportRequest(
      input_path=artifact_root,
      llm_provider="openai-compatible",
      llm_model="gpt-4.1-mini",
    )
  )

  metadata_payload = json.loads((artifact_root / "metadata.json").read_text(encoding="utf-8"))
  assert result.remote_provider_selected is True
  assert metadata_payload["workflow"]["llm_provider"] == "openai-compatible"
  assert metadata_payload["workflow"]["llm_model"] == "gpt-4.1-mini"
