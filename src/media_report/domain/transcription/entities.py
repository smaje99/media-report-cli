from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TranscriptionRequest:
    audio_path: Path
    requested_language: str | None = None
    model_override: str | None = None
    device_preference: str = "auto"


@dataclass(frozen=True)
class TranscriptionSegment:
    index: int
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.end_seconds < self.start_seconds:
            raise ValueError("Transcription segment end_seconds must be >= start_seconds.")
        if not self.text.strip():
            raise ValueError("Transcription segment text must not be blank.")

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "index": self.index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
        }
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> TranscriptionSegment:
        confidence = payload.get("confidence")
        return cls(
            index=int(payload["index"]),
            start_seconds=float(payload["start_seconds"]),
            end_seconds=float(payload["end_seconds"]),
            text=str(payload["text"]),
            confidence=float(confidence) if confidence is not None else None,
        )


@dataclass(frozen=True)
class TranscriptionResult:
    provider: str
    model: str
    requested_language: str | None
    detected_language: str | None
    segments: tuple[TranscriptionSegment, ...]
    duration_ms: int
    device_preference: str = "auto"
    effective_device: str = "cpu"
    device_fallback_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("Transcription provider must not be blank.")
        if not self.model.strip():
            raise ValueError("Transcription model must not be blank.")
        if not self.device_preference.strip():
            raise ValueError("Transcription device_preference must not be blank.")
        if not self.effective_device.strip():
            raise ValueError("Transcription effective_device must not be blank.")
        if self.duration_ms < 0:
            raise ValueError("Transcription duration_ms must be >= 0.")
        if not self.has_usable_segments():
            raise ValueError("Transcription result must contain at least one usable segment.")

    @property
    def raw_text(self) -> str:
        return "\n".join(segment.text for segment in self.segments)

    def has_usable_segments(self) -> bool:
        return any(segment.text.strip() for segment in self.segments)

    def to_artifact_payload(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "requested_language": self.requested_language,
            "detected_language": self.detected_language,
            "segments": [segment.to_payload() for segment in self.segments],
        }

    @classmethod
    def from_artifact_payload(
        cls,
        payload: dict[str, Any],
        *,
        duration_ms: int = 0,
    ) -> TranscriptionResult:
        segments_payload = payload["segments"]
        if not isinstance(segments_payload, list):
            raise ValueError("Transcription artifact payload must contain a list of segments.")
        return cls(
            provider=str(payload["provider"]),
            model=str(payload["model"]),
            requested_language=payload.get("requested_language"),
            detected_language=payload.get("detected_language"),
            segments=tuple(
                TranscriptionSegment.from_payload(segment_payload)
                for segment_payload in segments_payload
            ),
            duration_ms=duration_ms,
        )
