from __future__ import annotations

from pathlib import Path


class FFmpegService:
    @staticmethod
    def build_extract_command(source_path: Path, output_path: Path) -> list[str]:
        return [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_path),
        ]
