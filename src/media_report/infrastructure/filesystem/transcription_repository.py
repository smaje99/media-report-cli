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
            payload = result.model_dump(mode="json")
            payload.pop("duration_ms", None)
            payload.pop("device_preference", None)
            payload.pop("effective_device", None)
            payload.pop("device_fallback_reason", None)
            for segment in payload["segments"]:
                if segment.get("confidence") is None:
                    segment.pop("confidence", None)
            transcript_segments_path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as exc:
            raise TranscriptionPersistenceError(
                "Failed to persist transcription artifacts."
            ) from exc
