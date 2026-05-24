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
