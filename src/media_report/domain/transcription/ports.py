from __future__ import annotations

from pathlib import Path
from typing import Protocol

from media_report.domain.transcription.entities import (
  TranscriptionRequest,
  TranscriptionResult,
)


class TranscriptionProvider(Protocol):
  def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
    """Transcribe an audio file."""


class TranscriptionArtifactRepository(Protocol):
  def write(
    self,
    *,
    result: TranscriptionResult,
    transcript_raw_path: Path,
    transcript_segments_path: Path,
  ) -> None:
    """Persist transcription artifacts."""
