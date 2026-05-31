from __future__ import annotations

from time import perf_counter
from typing import Any

from media_report.core.errors import (
    OptionalDependencyMissingError,
    TranscriptionExecutionError,
    TranscriptionModelError,
    TranscriptionOutputError,
)
from media_report.domain.transcription.entities import (
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionSegment,
)
from media_report.domain.transcription.ports import TranscriptionProvider
from media_report.infrastructure.transcription.capabilities import (
    TRANSCRIPTION_PROVIDER,
    load_faster_whisper_module,
)


class FasterWhisperProvider(TranscriptionProvider):
    def __init__(self, *, default_model: str) -> None:
        self._default_model = default_model

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        module = load_faster_whisper_module()
        effective_model = request.model_override or self._default_model

        try:
            model = module.WhisperModel(effective_model)
        except OptionalDependencyMissingError:
            raise
        except Exception as exc:
            raise TranscriptionModelError(
                provider=TRANSCRIPTION_PROVIDER,
                model=effective_model,
                detail=_error_detail(exc),
            ) from exc

        started_at = perf_counter()
        try:
            raw_segments, info = model.transcribe(
                str(request.audio_path),
                language=request.requested_language,
            )
            segments = tuple(raw_segments)
        except Exception as exc:
            raise TranscriptionExecutionError(
                provider=TRANSCRIPTION_PROVIDER,
                model=effective_model,
                audio_path=str(request.audio_path),
                detail=_error_detail(exc),
            ) from exc

        duration_ms = int((perf_counter() - started_at) * 1000)
        detected_language = _normalize_language(getattr(info, "language", None))

        try:
            mapped_segments = tuple(
                _map_segment(index=index, raw_segment=segment)
                for index, segment in enumerate(segments)
            )
            return TranscriptionResult(
                provider=TRANSCRIPTION_PROVIDER,
                model=effective_model,
                requested_language=request.requested_language,
                detected_language=detected_language,
                segments=mapped_segments,
                duration_ms=duration_ms,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise TranscriptionOutputError(
                f"{TRANSCRIPTION_PROVIDER} returned invalid transcription output."
            ) from exc


def _map_segment(*, index: int, raw_segment: Any) -> TranscriptionSegment:
    segment_index = getattr(raw_segment, "id", index)
    confidence = _normalize_confidence(getattr(raw_segment, "confidence", None))
    return TranscriptionSegment(
        index=int(segment_index),
        start_seconds=float(raw_segment.start),
        end_seconds=float(raw_segment.end),
        text=str(raw_segment.text),
        confidence=confidence,
    )


def _normalize_language(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_confidence(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, int | float) else None


def _error_detail(error: Exception) -> str:
    detail = str(error).strip()
    return detail or error.__class__.__name__
