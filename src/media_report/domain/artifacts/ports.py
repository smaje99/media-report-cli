from __future__ import annotations

from pathlib import Path
from typing import Protocol

from media_report.domain.artifacts.entities import PipelineMetadata


class PipelineMetadataRepository(Protocol):
    """Repository for reading and writing pipeline metadata."""

    def read(self, path: Path) -> PipelineMetadata:
        """Load pipeline metadata from the given path."""

    def write(self, metadata: PipelineMetadata) -> None:
        """Persist pipeline metadata to the path described by the metadata itself."""
