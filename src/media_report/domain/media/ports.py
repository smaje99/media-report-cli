from __future__ import annotations

from typing import Protocol

from media_report.domain.media.entities import (
  ExtractAudioRequest,
  MediaProcessingResult,
  NormalizeAudioRequest,
)


class MediaProcessingService(Protocol):
  def extract_audio(self, request: ExtractAudioRequest) -> MediaProcessingResult:
    """Extract audio from a supported media source."""

  def normalize_audio(self, request: NormalizeAudioRequest) -> MediaProcessingResult:
    """Normalize extracted audio for downstream processing."""
