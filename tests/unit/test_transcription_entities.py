from pathlib import Path

import pytest

from media_report.domain.transcription.entities import (
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionSegment,
)


def test_transcription_result_derives_raw_text_from_segments() -> None:
    result = TranscriptionResult(
        provider="stub",
        model="stub-small",
        requested_language="es",
        detected_language="es",
        segments=(
            TranscriptionSegment(
                index=0,
                start_seconds=0.0,
                end_seconds=1.0,
                text="hola",
            ),
            TranscriptionSegment(
                index=1,
                start_seconds=1.0,
                end_seconds=2.0,
                text="mundo",
                confidence=0.9,
            ),
        ),
        duration_ms=321,
    )

    assert result.raw_text == "hola\nmundo"
    assert result.model_dump(mode="json")["segments"][1]["confidence"] == pytest.approx(0.9)
    assert TranscriptionResult.model_validate(result.model_dump(mode="json")) == result


def test_transcription_result_rejects_empty_segments() -> None:
    with pytest.raises(ValueError, match="at least one usable segment"):
        TranscriptionResult(
            provider="stub",
            model="stub-small",
            requested_language=None,
            detected_language=None,
            segments=(),
            duration_ms=10,
        )


def test_transcription_segment_rejects_blank_text() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        TranscriptionSegment(
            index=0,
            start_seconds=0.0,
            end_seconds=1.0,
            text="   ",
        )


def test_transcription_request_keeps_audio_path_and_overrides() -> None:
    request = TranscriptionRequest(
        audio_path=Path("/tmp/audio.wav"),
        requested_language="en",
        model_override="small",
    )

    assert request.audio_path.name == "audio.wav"
    assert request.requested_language == "en"
    assert request.model_override == "small"
