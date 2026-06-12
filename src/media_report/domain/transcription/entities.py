from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


class TranscriptionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    audio_path: Path
    requested_language: str | None = None
    model_override: str | None = None
    device_preference: str = "auto"


class TranscriptionSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int
    start_seconds: Annotated[float, Field(ge=0)]
    end_seconds: Annotated[float, Field(ge=0)]
    text: str
    confidence: Annotated[float | None, Field(ge=0, le=1)] = None

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Transcription segment text must not be blank.")
        return value

    @model_validator(mode="after")
    def _validate_time_range(self) -> TranscriptionSegment:
        if self.end_seconds < self.start_seconds:
            raise ValueError("Transcription segment end_seconds must be >= start_seconds.")
        return self


class TranscriptionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    model: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    requested_language: str | None
    detected_language: str | None
    segments: tuple[TranscriptionSegment, ...]
    duration_ms: Annotated[int, Field(ge=0)] = 0
    device_preference: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ] = "auto"
    effective_device: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ] = "cpu"
    device_fallback_reason: str | None = None

    @model_validator(mode="after")
    def _validate_segments(self) -> TranscriptionResult:
        if not self.has_usable_segments():
            raise ValueError("Transcription result must contain at least one usable segment.")
        return self

    @property
    def raw_text(self) -> str:
        return "\n".join(segment.text for segment in self.segments)

    def has_usable_segments(self) -> bool:
        return any(segment.text.strip() for segment in self.segments)
