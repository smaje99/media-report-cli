"""Transcription ports and models."""

from media_report.domain.transcription.entities import (
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionSegment,
)
from media_report.domain.transcription.ports import TranscriptionProvider

__all__ = [
    "TranscriptionProvider",
    "TranscriptionRequest",
    "TranscriptionResult",
    "TranscriptionSegment",
]
