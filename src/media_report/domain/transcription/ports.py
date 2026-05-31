from __future__ import annotations

from typing import Protocol

from media_report.domain.transcription.entities import (
    TranscriptionRequest,
    TranscriptionResult,
)


class TranscriptionProvider(Protocol):
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        """Transcribe an audio file."""
