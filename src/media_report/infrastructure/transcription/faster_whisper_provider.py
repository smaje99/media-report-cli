from __future__ import annotations

from pathlib import Path

from media_report.domain.transcription.ports import TranscriptionProvider


class FasterWhisperProvider(TranscriptionProvider):
    def transcribe(self, audio_path: Path) -> str:
        raise NotImplementedError("faster-whisper integration is planned for a later phase.")
