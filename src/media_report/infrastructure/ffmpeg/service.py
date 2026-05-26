from __future__ import annotations

import subprocess
from pathlib import Path
from time import perf_counter

from media_report.core.errors import (
    FFmpegNotAvailableError,
    MediaProcessingExecutionError,
    MediaProcessingOutputError,
)
from media_report.domain.media.entities import (
    ExtractAudioRequest,
    MediaProcessingResult,
    NormalizeAudioRequest,
)
from media_report.domain.media.ports import MediaProcessingService

_STDERR_SUMMARY_LIMIT = 240


class FFmpegService(MediaProcessingService):
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

    @staticmethod
    def build_normalize_command(source_path: Path, output_path: Path) -> list[str]:
        return [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-af",
            "loudnorm",
            str(output_path),
        ]

    def extract_audio(self, request: ExtractAudioRequest) -> MediaProcessingResult:
        command = self.build_extract_command(request.source.path, request.output_path)
        return self._run_command(
            command=command,
            operation="extract_audio",
            output_path=request.output_path,
        )

    def normalize_audio(self, request: NormalizeAudioRequest) -> MediaProcessingResult:
        command = self.build_normalize_command(request.source_path, request.output_path)
        return self._run_command(
            command=command,
            operation="normalize_audio",
            output_path=request.output_path,
        )

    def _run_command(
        self,
        *,
        command: list[str],
        operation: str,
        output_path: Path,
    ) -> MediaProcessingResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        started_at = perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise FFmpegNotAvailableError("ffmpeg is not available in PATH.") from exc

        duration_ms = int((perf_counter() - started_at) * 1000)
        stderr_summary = self._summarize_stderr(completed.stderr)

        if completed.returncode != 0:
            raise MediaProcessingExecutionError(
                operation=operation,
                exit_code=completed.returncode,
                stderr_summary=stderr_summary,
            )

        if not output_path.exists():
            raise MediaProcessingOutputError(
                f"ffmpeg reported success for '{operation}' but did not generate "
                f"'{output_path.name}'."
            )

        return MediaProcessingResult(
            output_path=output_path,
            command=tuple(command),
            duration_ms=duration_ms,
            stderr_summary=stderr_summary,
        )

    @staticmethod
    def _summarize_stderr(stderr: str | None) -> str | None:
        if not stderr:
            return None
        if compact := " ".join(stderr.split()):
            return (
                compact
                if len(compact) <= _STDERR_SUMMARY_LIMIT
                else f"{compact[:_STDERR_SUMMARY_LIMIT - 3]}..."
            )
        else:
            return None
