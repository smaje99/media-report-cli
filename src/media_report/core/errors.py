from __future__ import annotations


class MediaReportError(Exception):
    """Base project error."""


class InputPathError(MediaReportError):
    """Raised when the requested input path is invalid or unsupported."""


class ArtifactConflictError(MediaReportError):
    """Raised when artifact output already exists and overwrite is disabled."""


class ArtifactMetadataError(MediaReportError):
    """Raised when persisted artifact metadata is missing, corrupt, or inconsistent."""


class ResumeNotPossibleError(MediaReportError):
    """Raised when the user requests resume semantics without a reusable artifact root."""


class StagePrerequisiteError(MediaReportError):
    """Raised when the requested stage selection cannot satisfy pipeline prerequisites."""


class TemplateNotFoundError(MediaReportError):
    """Raised when a packaged template cannot be resolved."""


class MediaProcessingError(MediaReportError):
    """Base error for media extraction and normalization failures."""


class FFmpegNotAvailableError(MediaProcessingError):
    """Raised when the ffmpeg binary is not available in PATH."""


class MediaProcessingExecutionError(MediaProcessingError):
    """Raised when a media processing command exits unsuccessfully."""

    def __init__(self, *, operation: str, exit_code: int, stderr_summary: str | None) -> None:
        message = (
            f"ffmpeg failed during '{operation}' with exit code {exit_code}: "
            f"{stderr_summary}" if stderr_summary else f"ffmpeg failed during '{operation}' with exit code {exit_code}."
        )
        super().__init__(message)
        self.operation = operation
        self.exit_code = exit_code
        self.stderr_summary = stderr_summary


class MediaProcessingOutputError(MediaProcessingError):
    """Raised when a media processing command does not produce its expected output."""
