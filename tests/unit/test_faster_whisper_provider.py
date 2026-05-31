from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from media_report.core.errors import (
    OptionalDependencyMissingError,
    TranscriptionExecutionError,
    TranscriptionModelError,
    TranscriptionOutputError,
)
from media_report.domain.transcription.entities import TranscriptionRequest
from media_report.infrastructure.transcription.capabilities import (
    TRANSCRIPTION_INSTALL_HINT,
    get_transcription_capability,
)
from media_report.infrastructure.transcription.faster_whisper_provider import (
    FasterWhisperProvider,
)

TEST_AUDIO_PATH = Path("/tmp/audio.wav")


class FakeSegment:
    def __init__(
        self,
        *,
        segment_id: int,
        start: float,
        end: float,
        text: str,
        confidence: float | None = None,
    ) -> None:
        self.id = segment_id
        self.start = start
        self.end = end
        self.text = text
        if confidence is not None:
            self.confidence = confidence


def test_get_transcription_capability_reports_missing_dependency(monkeypatch) -> None:
    def fake_import(name: str):  # type: ignore[no-untyped-def]
        raise ImportError(name)

    monkeypatch.setattr(
        "media_report.infrastructure.transcription.capabilities.importlib.import_module",
        fake_import,
    )

    capability = get_transcription_capability()

    assert capability.available is False
    assert capability.provider == "faster-whisper"
    assert TRANSCRIPTION_INSTALL_HINT in capability.detail


def test_get_transcription_capability_reports_available_dependency(monkeypatch) -> None:
    monkeypatch.setattr(
        "media_report.infrastructure.transcription.capabilities.importlib.import_module",
        lambda name: SimpleNamespace(),
    )

    capability = get_transcription_capability()

    assert capability.available is True
    assert capability.provider == "faster-whisper"
    assert capability.install_hint is None


def test_provider_raises_actionable_error_when_dependency_is_missing(monkeypatch) -> None:
    def fake_import(name: str):  # type: ignore[no-untyped-def]
        raise ImportError(name)

    monkeypatch.setattr(
        "media_report.infrastructure.transcription.capabilities.importlib.import_module",
        fake_import,
    )

    provider = FasterWhisperProvider(default_model="small")
    request = TranscriptionRequest(audio_path=TEST_AUDIO_PATH)

    with pytest.raises(OptionalDependencyMissingError, match="Install it with") as exc_info:
        provider.transcribe(request)

    assert TRANSCRIPTION_INSTALL_HINT in str(exc_info.value)


def test_provider_uses_model_override_and_maps_segments(monkeypatch) -> None:
    calls: list[tuple[str, str, str | None]] = []

    class FakeWhisperModel:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        def transcribe(self, audio_path: str, language: str | None = None):  # type: ignore[no-untyped-def]
            calls.append((self.model_name, audio_path, language))
            return (
                [
                    FakeSegment(
                        segment_id=3,
                        start=0.0,
                        end=1.25,
                        text="hola",
                        confidence=0.87,
                    ),
                    FakeSegment(
                        segment_id=4,
                        start=1.25,
                        end=2.5,
                        text="mundo",
                    ),
                ],
                SimpleNamespace(language="es"),
            )

    monkeypatch.setattr(
        "media_report.infrastructure.transcription.capabilities.importlib.import_module",
        lambda name: SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    provider = FasterWhisperProvider(default_model="small")
    result = provider.transcribe(
        TranscriptionRequest(
            audio_path=TEST_AUDIO_PATH,
            requested_language="es",
            model_override="large-v3",
        )
    )

    assert calls == [("large-v3", str(TEST_AUDIO_PATH), "es")]
    assert result.provider == "faster-whisper"
    assert result.model == "large-v3"
    assert result.requested_language == "es"
    assert result.detected_language == "es"
    assert result.raw_text == "hola\nmundo"
    assert result.segments[0].index == 3
    assert result.segments[0].confidence == pytest.approx(0.87)
    assert result.duration_ms >= 0


def test_provider_maps_model_initialization_failures(monkeypatch) -> None:
    class FailingWhisperModel:
        def __init__(self, model_name: str) -> None:
            raise RuntimeError(f"unknown model {model_name}")

    monkeypatch.setattr(
        "media_report.infrastructure.transcription.capabilities.importlib.import_module",
        lambda name: SimpleNamespace(WhisperModel=FailingWhisperModel),
    )

    provider = FasterWhisperProvider(default_model="broken")

    with pytest.raises(TranscriptionModelError, match="unknown model broken"):
        provider.transcribe(TranscriptionRequest(audio_path=TEST_AUDIO_PATH))


def test_provider_maps_execution_failures(monkeypatch) -> None:
    class FakeWhisperModel:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        def transcribe(self, audio_path: str, language: str | None = None):  # type: ignore[no-untyped-def]
            raise RuntimeError("decoder crashed")

    monkeypatch.setattr(
        "media_report.infrastructure.transcription.capabilities.importlib.import_module",
        lambda name: SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    provider = FasterWhisperProvider(default_model="small")

    with pytest.raises(TranscriptionExecutionError, match="decoder crashed"):
        provider.transcribe(TranscriptionRequest(audio_path=TEST_AUDIO_PATH))


def test_provider_rejects_empty_or_invalid_output(monkeypatch) -> None:
    class FakeWhisperModel:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        def transcribe(self, audio_path: str, language: str | None = None):  # type: ignore[no-untyped-def]
            return ([], SimpleNamespace(language=None))

    monkeypatch.setattr(
        "media_report.infrastructure.transcription.capabilities.importlib.import_module",
        lambda name: SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    provider = FasterWhisperProvider(default_model="small")

    with pytest.raises(TranscriptionOutputError, match="invalid transcription output"):
        provider.transcribe(TranscriptionRequest(audio_path=TEST_AUDIO_PATH))
