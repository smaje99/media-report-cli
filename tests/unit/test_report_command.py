from __future__ import annotations

from pathlib import Path

import pytest

from media_report.cli.commands.report import _resolve_report_input_path
from media_report.core.errors import InputPathError, ResumeNotPossibleError
from media_report.domain.artifacts.entities import PipelineStage
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaSource
from media_report.infrastructure.filesystem.metadata_repository import (
  JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


def write_artifact_root(media_path: Path) -> Path:
  planner = ArtifactPlanner()
  artifacts = planner.prepare_new(media_path)
  source = FileSystemMediaScanner().classify(media_path)
  metadata = planner.bootstrap_metadata(
    source=MediaSource(path=media_path, kind=source.kind),
    artifact_plan=artifacts,
    template_name="generic",
    llm_provider="ollama",
    llm_model="llama3.1",
    output_format="pdf",
    language=None,
    selected_stages=tuple(PipelineStage),
  )
  JsonPipelineMetadataRepository().write(metadata)
  planner.initialize_log(artifacts.root_dir, metadata_schema_version=metadata.schema_version)
  return artifacts.root_dir


def test_resolve_report_input_accepts_artifact_root(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  artifact_root = write_artifact_root(media_path)

  resolved = _resolve_report_input_path(artifact_root)

  assert resolved == artifact_root


def test_resolve_report_input_maps_media_file_to_sibling_artifact_root(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")
  artifact_root = write_artifact_root(media_path)

  resolved = _resolve_report_input_path(media_path)

  assert resolved == artifact_root


def test_resolve_report_input_rejects_media_file_without_artifact_root(tmp_path: Path) -> None:
  media_path = tmp_path / "meeting.mp3"
  media_path.write_text("audio", encoding="utf-8")

  with pytest.raises(ResumeNotPossibleError):
    _resolve_report_input_path(media_path)


def test_resolve_report_input_rejects_missing_path(tmp_path: Path) -> None:
  with pytest.raises(InputPathError):
    _resolve_report_input_path(tmp_path / "missing.mp3")
