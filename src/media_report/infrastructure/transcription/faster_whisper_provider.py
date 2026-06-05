from __future__ import annotations

import platform
from collections.abc import Iterable
from time import perf_counter
from typing import Protocol

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


class _RawSegment(Protocol):
    """Minimal faster-whisper segment shape consumed by this adapter only."""

    start: float
    end: float
    text: str


class _WhisperModelInstance(Protocol):
    """Minimal transcriber interface returned by the faster-whisper SDK."""

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
    ) -> tuple[Iterable[_RawSegment], object]:
        """Transcribe an audio file."""


class _WhisperModelFactory(Protocol):
    """Constructor shape exposed by the faster-whisper module."""

    def __call__(
        self,
        model_name: str,
        *,
        device: str,
    ) -> _WhisperModelInstance:
        """Instantiate a faster-whisper model."""


class _WhisperModule(Protocol):
    """Subset of the faster-whisper module required by this adapter."""

    WhisperModel: _WhisperModelFactory


class FasterWhisperProvider(TranscriptionProvider):
    """
    Adapt the faster-whisper SDK to the stable domain `TranscriptionProvider` port.

    The private protocols above are intentionally infrastructure-local: they describe
    only the minimal SDK surface this adapter needs for typing, and they are not part
    of the project's public or domain-level contracts.
    """

    def __init__(self, *, default_model: str) -> None:
        self._default_model = default_model

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        module = load_faster_whisper_module()
        effective_model = request.model_override or self._default_model
        model, effective_device, device_fallback_reason = self._build_model(
            module=module,
            effective_model=effective_model,
            device_preference=request.device_preference,
        )

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
                device_preference=request.device_preference,
                effective_device=effective_device,
                device_fallback_reason=device_fallback_reason,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise TranscriptionOutputError(
                f"{TRANSCRIPTION_PROVIDER} returned invalid transcription output."
            ) from exc

    def _build_model(
        self,
        *,
        module: _WhisperModule,
        effective_model: str,
        device_preference: str,
    ) -> tuple[_WhisperModelInstance, str, str | None]:
        candidates = _device_candidates(device_preference)
        failures: list[tuple[str, str]] = []

        for device in candidates:
            try:
                return (
                    module.WhisperModel(effective_model, device=device),
                    device,
                    _fallback_reason(
                        requested=device_preference,
                        effective=device,
                        failures=failures,
                    ),
                )
            except OptionalDependencyMissingError:
                raise
            except Exception as exc:
                detail = _error_detail(exc)
                failures.append((device, detail))
                if device_preference != "auto":
                    raise TranscriptionModelError(
                        provider=TRANSCRIPTION_PROVIDER,
                        model=effective_model,
                        detail=f"device '{device}' failed: {detail}",
                    ) from exc

        failure_detail = ", ".join(
            f"{device}: {detail}" for device, detail in failures
        ) or "unable to initialize any device"
        raise TranscriptionModelError(
            provider=TRANSCRIPTION_PROVIDER,
            model=effective_model,
            detail=f"device selection failed ({failure_detail})",
        )


def _map_segment(*, index: int, raw_segment: _RawSegment) -> TranscriptionSegment:
    segment_index = getattr(raw_segment, "id", index)
    confidence = _normalize_confidence(getattr(raw_segment, "confidence", None))
    return TranscriptionSegment(
        index=int(segment_index),
        start_seconds=float(raw_segment.start),
        end_seconds=float(raw_segment.end),
        text=str(raw_segment.text),
        confidence=confidence,
    )


def _normalize_language(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_confidence(value: object | None) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, int | float) else None


def _device_candidates(device_preference: str) -> tuple[str, ...]:
    if device_preference != "auto":
        return (device_preference,)

    os_name = platform.system().lower()
    fallback_devices = ("cuda", "cpu") if os_name == "linux" else ("cpu",)
    return ("mps", "cpu") if os_name == "darwin" else fallback_devices


def _fallback_reason(
    *,
    requested: str,
    effective: str,
    failures: list[tuple[str, str]],
) -> str | None:
    if requested != "auto" or not failures:
        return None
    attempted = ", ".join(f"{device}: {detail}" for device, detail in failures)
    return f"auto fallback to '{effective}' after {attempted}"


def _error_detail(error: Exception) -> str:
    detail = str(error).strip()
    return detail or error.__class__.__name__
