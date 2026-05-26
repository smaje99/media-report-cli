from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from media_report.core.errors import (
    FFmpegNotAvailableError,
    MediaProcessingExecutionError,
    MediaProcessingOutputError,
)
from media_report.domain.media.entities import (
    ExtractAudioRequest,
    MediaKind,
    MediaSource,
    NormalizeAudioRequest,
)
from media_report.infrastructure.ffmpeg.service import FFmpegService


def test_extract_audio_maps_missing_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    service = FFmpegService()
    source_path = tmp_path / "meeting.mp4"
    source_path.write_text("video", encoding="utf-8")
    output_path = tmp_path / "audio_extracted.wav"

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("media_report.infrastructure.ffmpeg.service.subprocess.run", fake_run)

    with pytest.raises(FFmpegNotAvailableError, match="ffmpeg is not available"):
        service.extract_audio(
            ExtractAudioRequest(
                source=MediaSource(path=source_path, kind=MediaKind.VIDEO),
                output_path=output_path,
            )
        )


def test_extract_audio_maps_non_zero_exit(monkeypatch, tmp_path: Path) -> None:
    service = FFmpegService()
    source_path = tmp_path / "meeting.wav"
    source_path.write_text("audio", encoding="utf-8")
    output_path = tmp_path / "audio_extracted.wav"

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="decoder error on source stream",
        )

    monkeypatch.setattr("media_report.infrastructure.ffmpeg.service.subprocess.run", fake_run)

    with pytest.raises(MediaProcessingExecutionError, match="extract_audio") as exc_info:
        service.extract_audio(
            ExtractAudioRequest(
                source=MediaSource(path=source_path, kind=MediaKind.AUDIO),
                output_path=output_path,
            )
        )

    assert exc_info.value.operation == "extract_audio"
    assert exc_info.value.exit_code == 1
    assert exc_info.value.stderr_summary == "decoder error on source stream"


def test_normalize_audio_requires_output_file(monkeypatch, tmp_path: Path) -> None:
    service = FFmpegService()
    source_path = tmp_path / "audio_extracted.wav"
    source_path.write_text("audio", encoding="utf-8")
    output_path = tmp_path / "audio_normalized.wav"

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr("media_report.infrastructure.ffmpeg.service.subprocess.run", fake_run)

    with pytest.raises(MediaProcessingOutputError, match="did not generate"):
        service.normalize_audio(
            NormalizeAudioRequest(
                source_path=source_path,
                output_path=output_path,
            )
        )


def test_normalize_audio_returns_result(monkeypatch, tmp_path: Path) -> None:
    service = FFmpegService()
    source_path = tmp_path / "audio_extracted.wav"
    source_path.write_text("audio", encoding="utf-8")
    output_path = tmp_path / "audio_normalized.wav"

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        output_path.write_text("normalized", encoding="utf-8")
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="",
            stderr="peak normalization completed",
        )

    monkeypatch.setattr("media_report.infrastructure.ffmpeg.service.subprocess.run", fake_run)

    result = service.normalize_audio(
        NormalizeAudioRequest(
            source_path=source_path,
            output_path=output_path,
        )
    )

    assert result.output_path == output_path
    assert result.command[0] == "ffmpeg"
    assert result.command[-1] == str(output_path)
    assert result.duration_ms >= 0
    assert result.stderr_summary == "peak normalization completed"
