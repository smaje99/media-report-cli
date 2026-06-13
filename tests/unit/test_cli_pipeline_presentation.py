from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from media_report.application.process_media.models import ProcessPlanItem
from media_report.application.reporting.models import GenerateReportResult
from media_report.application.transcribe.models import TranscribeResult
from media_report.cli.presentation.pipeline_runs import (
  REPORT_DISPLAY_STAGES,
  build_process_runs_table,
  build_report_run_table,
  build_run_detail_lines,
  build_transcribe_run_table,
  format_stage_decisions,
  format_transcription_runtime,
)
from media_report.domain.artifacts.entities import (
  ArtifactPlan,
  PipelineMetadata,
  PipelineStage,
  StageDecision,
)
from media_report.domain.artifacts.service import ArtifactPlanner, PipelineStatePlanner
from media_report.domain.media.entities import MediaKind, MediaSource
from media_report.domain.transcription.entities import (
  TranscriptionResult as DomainTranscriptionResult,
)
from media_report.domain.transcription.entities import TranscriptionSegment


def render_table(table: Table) -> str:
  console = Console(record=True, width=140)
  console.print(table)
  return console.export_text()


def build_metadata(media_path: Path) -> tuple[ArtifactPlan, PipelineMetadata]:
  planner = ArtifactPlanner()
  source = MediaSource(path=media_path, kind=MediaKind.AUDIO)
  artifacts = planner.plan(media_path)
  metadata = planner.bootstrap_metadata(
    source=source,
    artifact_plan=artifacts,
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
  metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.EXTRACT_AUDIO)
  metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.NORMALIZE_AUDIO)
  metadata = planner.record_transcription(metadata, result=build_transcription_result())
  metadata = planner.mark_stage_completed(metadata, stage=PipelineStage.TRANSCRIBE)
  return artifacts, metadata


def build_transcription_result() -> DomainTranscriptionResult:
  return DomainTranscriptionResult(
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
    device_fallback_reason="auto fallback to 'cpu' after cuda: unavailable",
  )


def build_stage_decisions() -> tuple[StageDecision, ...]:
  return PipelineStatePlanner().plan_new(
    (
      PipelineStage.EXTRACT_AUDIO,
      PipelineStage.NORMALIZE_AUDIO,
      PipelineStage.TRANSCRIBE,
    )
  )


def test_format_stage_decisions_includes_stage_and_reason() -> None:
  formatted = format_stage_decisions(build_stage_decisions())

  assert "extract_audio: planned" in formatted
  assert "(" in formatted


def test_format_transcription_runtime_includes_fallback() -> None:
  _, metadata = build_metadata(Path("meeting.mp3"))
  formatted = format_transcription_runtime(metadata.transcription)

  assert "faster-whisper/small" in formatted
  assert "device=cpu" in formatted
  assert "auto fallback to 'cpu'" in formatted


def test_build_transcribe_run_table_renders_single_run_summary(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  artifacts, metadata = build_metadata(media_path)
  result = TranscribeResult(
    source=MediaSource(path=media_path, kind=MediaKind.AUDIO),
    artifacts=artifacts,
    stage_decisions=build_stage_decisions(),
    final_metadata=metadata,
  )

  rendered = render_table(build_transcribe_run_table(result))

  assert "Transcription Run" in rendered
  assert "audio" in rendered
  assert "extract_audio: completed" in rendered
  assert "faster-whisper/small" in rendered


def test_build_process_runs_table_renders_multiple_sources(tmp_path: Path) -> None:
  first_path = tmp_path / "meeting.mp3"
  second_path = tmp_path / "lecture.mp3"
  first_artifacts, first_metadata = build_metadata(first_path)
  second_artifacts, second_metadata = build_metadata(second_path)
  items = (
    ProcessPlanItem(
      source=MediaSource(path=first_path, kind=MediaKind.AUDIO),
      artifacts=first_artifacts,
      template_name="generic",
      stage_decisions=build_stage_decisions(),
      final_metadata=first_metadata,
    ),
    ProcessPlanItem(
      source=MediaSource(path=second_path, kind=MediaKind.AUDIO),
      artifacts=second_artifacts,
      template_name="meeting",
      stage_decisions=build_stage_decisions(),
      final_metadata=second_metadata,
    ),
  )

  rendered = render_table(build_process_runs_table(items))

  assert "Media Runs" in rendered
  assert rendered.count("faster-whisper/small") == 2
  assert "meeting" in rendered


def test_build_run_detail_lines_preserves_runtime_and_status_lines(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  _, metadata = build_metadata(media_path)

  lines = build_run_detail_lines(
    source_name=media_path.name,
    stage_decisions=build_stage_decisions(),
    metadata=metadata,
  )

  assert f"{media_path.name} :: extract_audio status: completed" in lines
  assert any("transcription runtime: faster-whisper/small device=cpu" in line for line in lines)
  assert any("transcription fallback:" in line for line in lines)


def test_build_report_run_table_renders_report_and_pdf_statuses(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  artifacts, metadata = build_metadata(media_path)
  result = GenerateReportResult(
    source=MediaSource(path=media_path, kind=MediaKind.AUDIO),
    artifacts=artifacts,
    stage_decisions=build_stage_decisions(),
    final_metadata=metadata,
    prompt_path=artifacts.prompt_used,
    response_path=artifacts.llm_response_raw,
    report_path=artifacts.report_markdown,
    rendered_prompt="prompt",
    llm_response="# Report",
    report_text="# Report\n",
    remote_provider_selected=False,
  )

  rendered = render_table(build_report_run_table(result))

  assert "Report Run" in rendered
  assert "report: skipped" in rendered
  assert "pdf: skipped" in rendered


def test_build_run_detail_lines_can_render_report_visible_stages(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  _, metadata = build_metadata(media_path)

  lines = build_run_detail_lines(
    source_name=media_path.name,
    stage_decisions=build_stage_decisions(),
    metadata=metadata,
    visible_stages=REPORT_DISPLAY_STAGES,
  )

  assert f"{media_path.name} :: report status: skipped" in lines
  assert f"{media_path.name} :: pdf status: skipped" in lines
