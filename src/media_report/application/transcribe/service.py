from __future__ import annotations

from media_report.application.transcribe.execution import TranscribeRunExecutor
from media_report.application.transcribe.models import TranscribeRequest, TranscribeResult
from media_report.application.transcribe.preparation import TranscribeRunPreparer
from media_report.domain.artifacts.ports import PipelineMetadataRepository
from media_report.domain.artifacts.service import (
  ArtifactPlanner,
  ArtifactRootValidator,
  PipelineStatePlanner,
)
from media_report.domain.media.ports import MediaProcessingService
from media_report.domain.transcription.ports import (
  TranscriptionArtifactRepository,
  TranscriptionProvider,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner


class TranscribeService:
  def __init__(
    self,
    *,
    scanner: FileSystemMediaScanner,
    metadata_repository: PipelineMetadataRepository,
    media_processor: MediaProcessingService,
    transcription_provider: TranscriptionProvider,
    transcription_artifact_repository: TranscriptionArtifactRepository,
  ) -> None:
    artifact_planner = ArtifactPlanner()
    self._preparer = TranscribeRunPreparer(
      scanner=scanner,
      metadata_repository=metadata_repository,
      artifact_planner=artifact_planner,
      artifact_validator=ArtifactRootValidator(),
      state_planner=PipelineStatePlanner(),
    )
    self._executor = TranscribeRunExecutor(
      metadata_repository=metadata_repository,
      media_processor=media_processor,
      transcription_provider=transcription_provider,
      transcription_artifact_repository=transcription_artifact_repository,
      artifact_planner=artifact_planner,
    )

  def transcribe(self, request: TranscribeRequest) -> TranscribeResult:
    prepared_run = self._preparer.prepare(request)
    final_metadata = self._executor.execute(prepared_run, request)
    return TranscribeResult(
      source=prepared_run.source,
      artifacts=prepared_run.artifacts,
      stage_decisions=prepared_run.stage_decisions,
      final_metadata=final_metadata,
    )
