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
        if stderr_summary:
            message = (
                f"ffmpeg failed during '{operation}' with exit code {exit_code}: "
                f"{stderr_summary}"
            )
        else:
            message = f"ffmpeg failed during '{operation}' with exit code {exit_code}."
        super().__init__(message)
        self.operation = operation
        self.exit_code = exit_code
        self.stderr_summary = stderr_summary


class MediaProcessingOutputError(MediaProcessingError):
    """Raised when a media processing command does not produce its expected output."""


class OptionalDependencyMissingError(MediaReportError):
    """Raised when an optional Python dependency is required for a feature."""

    def __init__(
        self,
        *,
        dependency_name: str,
        feature_name: str,
        install_hint: str,
    ) -> None:
        message = (
            f"Optional dependency '{dependency_name}' is required for {feature_name}. "
            f"Install it with {install_hint}"
        )
        super().__init__(message)
        self.dependency_name = dependency_name
        self.feature_name = feature_name
        self.install_hint = install_hint


class TranscriptionModelError(MediaReportError):
    """Raised when a transcription provider cannot initialize its model."""

    def __init__(self, *, provider: str, model: str, detail: str | None = None) -> None:
        message = f"{provider} could not initialize model '{model}'."
        if detail:
            message = f"{message} {detail}"
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.detail = detail


class TranscriptionExecutionError(MediaReportError):
    """Raised when a transcription provider fails while processing audio."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        audio_path: str,
        detail: str | None = None,
    ) -> None:
        message = (
            f"{provider} failed to transcribe '{audio_path}' with model '{model}'."
        )
        if detail:
            message = f"{message} {detail}"
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.audio_path = audio_path
        self.detail = detail


class TranscriptionOutputError(MediaReportError):
    """Raised when a transcription provider returns invalid output."""


class TranscriptionPersistenceError(MediaReportError):
    """Raised when transcription artifacts cannot be persisted safely."""
