from __future__ import annotations

from pathlib import Path
from typing import Protocol


class MediaProcessingService(Protocol):
    def extract_audio(self, source_path: Path, output_path: Path) -> None:
        """Extract or normalize media artifacts."""
