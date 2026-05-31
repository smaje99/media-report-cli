from __future__ import annotations

from media_report.domain.transcription.entities import TranscriptionRequest, TranscriptionResult
from media_report.domain.transcription.ports import TranscriptionProvider


class FasterWhisperProvider(TranscriptionProvider):
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        raise NotImplementedError("faster-whisper integration is planned for a later phase.")
