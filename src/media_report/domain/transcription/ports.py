from __future__ import annotations

from pathlib import Path
from typing import Protocol


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: Path) -> str:
        """Transcribe an audio file."""
