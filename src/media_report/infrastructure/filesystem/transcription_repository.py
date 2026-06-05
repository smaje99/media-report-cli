from __future__ import annotations

import json
from pathlib import Path

from media_report.core.errors import TranscriptionPersistenceError
from media_report.domain.transcription.entities import TranscriptionResult


class JsonTranscriptionArtifactRepository:
    """Persist transcription artifacts to the filesystem."""

    def write(
        self,
        *,
        result: TranscriptionResult,
        transcript_raw_path: Path,
        transcript_segments_path: Path,
    ) -> None:
        try:
            transcript_raw_path.write_text(f"{result.raw_text}\n", encoding="utf-8")
            transcript_segments_path.write_text(
                json.dumps(result.to_artifact_payload(), indent=2),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as exc:
            raise TranscriptionPersistenceError(
                "Failed to persist transcription artifacts."
            ) from exc
