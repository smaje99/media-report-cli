from __future__ import annotations

from typing import Protocol

from media_report.application.transcribe.models import TranscribeRequest, TranscribeResult


class TranscribeUseCase(Protocol):
    """Application contract for transcript artifact generation."""

    def transcribe(self, request: TranscribeRequest) -> TranscribeResult:
        """Execute the transcription workflow for a single input."""
