from __future__ import annotations


class MediaReportError(Exception):
    """Base project error."""


class InputPathError(MediaReportError):
    """Raised when the requested input path is invalid or unsupported."""


class ArtifactConflictError(MediaReportError):
    """Raised when artifact output already exists and overwrite is disabled."""


class TemplateNotFoundError(MediaReportError):
    """Raised when a packaged template cannot be resolved."""
