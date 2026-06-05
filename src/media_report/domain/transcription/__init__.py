"""Transcription ports and models."""

from media_report.domain.transcription.entities import (
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionSegment,
)
from media_report.domain.transcription.ports import (
    TranscriptionArtifactRepository,
    TranscriptionProvider,
)

__all__ = [
    "TranscriptionArtifactRepository",
    "TranscriptionProvider",
    "TranscriptionRequest",
    "TranscriptionResult",
    "TranscriptionSegment",
]
