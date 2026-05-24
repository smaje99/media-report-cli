from __future__ import annotations

import json
from pathlib import Path

from media_report.core.errors import ArtifactMetadataError
from media_report.domain.artifacts.entities import PipelineMetadata


class JsonPipelineMetadataRepository:
    """Repository for reading and writing pipeline metadata as JSON files."""

    def read(self, path: Path) -> PipelineMetadata:
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return PipelineMetadata.from_payload(payload)
        except FileNotFoundError:
            raise
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ArtifactMetadataError(f"Invalid artifact metadata: {path}.") from exc

    def write(self, metadata: PipelineMetadata) -> None:
        target = Path(metadata.artifacts.metadata_json)
        target.write_text(json.dumps(metadata.to_payload(), indent=2), encoding="utf-8")
