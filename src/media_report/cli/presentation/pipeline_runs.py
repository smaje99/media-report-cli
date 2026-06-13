from __future__ import annotations

from collections.abc import Sequence

from rich.table import Table

from media_report.application.process_media.models import ProcessPlanItem
from media_report.application.reporting.models import GenerateReportResult
from media_report.application.transcribe.models import TranscribeResult
from media_report.domain.artifacts.entities import (
  PipelineMetadata,
  PipelineStage,
  PipelineTranscriptionMetadata,
  StageDecision,
)

TRANSCRIPTION_DISPLAY_STAGES = (
  PipelineStage.EXTRACT_AUDIO,
  PipelineStage.NORMALIZE_AUDIO,
  PipelineStage.TRANSCRIBE,
)
REPORT_DISPLAY_STAGES = (
  PipelineStage.EXTRACT_AUDIO,
  PipelineStage.NORMALIZE_AUDIO,
  PipelineStage.TRANSCRIBE,
  PipelineStage.REPORT,
  PipelineStage.PDF,
)


def format_stage_decisions(stage_decisions: tuple[StageDecision, ...]) -> str:
  return "\n".join(
    f"{decision.stage.value}: {decision.decision.value} ({decision.reason})"
    for decision in stage_decisions
  )


def format_stage_statuses(
  metadata: PipelineMetadata,
  *,
  visible_stages: Sequence[PipelineStage] = TRANSCRIPTION_DISPLAY_STAGES,
) -> str:
  return "\n".join(
    f"{stage.value}: {metadata.stages[stage].status.value}" for stage in visible_stages
  )


def format_transcription_runtime(transcription: PipelineTranscriptionMetadata | None) -> str:
  if transcription is None:
    return "-"

  runtime = (
    f"{transcription.provider}/{transcription.model}\ndevice={transcription.effective_device}"
  )
  if transcription.device_fallback_reason:
    return f"{runtime}\n{transcription.device_fallback_reason}"
  return runtime


def build_process_runs_table(
  items: tuple[ProcessPlanItem, ...],
  *,
  visible_stages: Sequence[PipelineStage] = TRANSCRIPTION_DISPLAY_STAGES,
) -> Table:
  table = Table(title="Media Runs")
  table.add_column("Source")
  table.add_column("Kind")
  table.add_column("Artifacts")
  table.add_column("Template")
  table.add_column("Stage Decisions")
  table.add_column("Stage Status")
  table.add_column("Runtime")

  for item in items:
    table.add_row(
      str(item.source.path),
      item.source.kind.value,
      str(item.artifacts.root_dir),
      item.template_name,
      format_stage_decisions(item.stage_decisions),
      format_stage_statuses(item.final_metadata, visible_stages=visible_stages),
      format_transcription_runtime(item.final_metadata.transcription),
    )

  return table


def build_transcribe_run_table(
  result: TranscribeResult,
  *,
  visible_stages: Sequence[PipelineStage] = TRANSCRIPTION_DISPLAY_STAGES,
) -> Table:
  table = Table(title="Transcription Run")
  table.add_column("Source")
  table.add_column("Kind")
  table.add_column("Artifacts")
  table.add_column("Stage Decisions")
  table.add_column("Stage Status")
  table.add_column("Runtime")
  table.add_row(
    str(result.source.path),
    result.source.kind.value,
    str(result.artifacts.root_dir),
    format_stage_decisions(result.stage_decisions),
    format_stage_statuses(result.final_metadata, visible_stages=visible_stages),
    format_transcription_runtime(result.final_metadata.transcription),
  )
  return table


def build_report_run_table(result: GenerateReportResult) -> Table:
  table = Table(title="Report Run")
  table.add_column("Source")
  table.add_column("Kind")
  table.add_column("Artifacts")
  table.add_column("Template")
  table.add_column("Stage Decisions")
  table.add_column("Stage Status")
  table.add_column("Runtime")
  table.add_row(
    str(result.source.path),
    result.source.kind.value,
    str(result.artifacts.root_dir),
    result.final_metadata.workflow.template_name,
    format_stage_decisions(result.stage_decisions),
    format_stage_statuses(result.final_metadata, visible_stages=REPORT_DISPLAY_STAGES),
    format_transcription_runtime(result.final_metadata.transcription),
  )
  return table


def build_run_detail_lines(
  *,
  source_name: str,
  stage_decisions: tuple[StageDecision, ...],
  metadata: PipelineMetadata,
  visible_stages: Sequence[PipelineStage] = TRANSCRIPTION_DISPLAY_STAGES,
) -> list[str]:
  lines = [
    f"{source_name} :: {decision.stage.value}: {decision.decision.value} - {decision.reason}"
    for decision in stage_decisions
  ]
  lines.extend(
    f"{source_name} :: {stage.value} status: {metadata.stages[stage].status.value}"
    for stage in visible_stages
  )
  if metadata.transcription is not None:
    lines.append(
      f"{source_name} :: transcription runtime: "
      f"{metadata.transcription.provider}/{metadata.transcription.model} "
      f"device={metadata.transcription.effective_device}"
    )
    if metadata.transcription.device_fallback_reason:
      lines.append(
        f"{source_name} :: transcription fallback: {metadata.transcription.device_fallback_reason}"
      )
  return lines
