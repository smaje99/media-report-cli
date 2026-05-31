from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import ModuleType

from media_report.core.errors import OptionalDependencyMissingError

TRANSCRIPTION_PROVIDER = "faster-whisper"
TRANSCRIPTION_INSTALL_HINT = (
    '`pip install "media-report-cli[transcription]"` or `uv sync --extra transcription`.'
)


@dataclass(frozen=True)
class TranscriptionCapability:
    provider: str
    available: bool
    detail: str
    install_hint: str | None = None


def load_faster_whisper_module() -> ModuleType:
    try:
        return importlib.import_module("faster_whisper")
    except ImportError as exc:
        raise OptionalDependencyMissingError(
            dependency_name="faster-whisper",
            feature_name="transcription",
            install_hint=TRANSCRIPTION_INSTALL_HINT,
        ) from exc


def get_transcription_capability() -> TranscriptionCapability:
    try:
        load_faster_whisper_module()
    except OptionalDependencyMissingError as exc:
        return TranscriptionCapability(
            provider=TRANSCRIPTION_PROVIDER,
            available=False,
            detail=str(exc),
            install_hint=TRANSCRIPTION_INSTALL_HINT,
        )

    return TranscriptionCapability(
        provider=TRANSCRIPTION_PROVIDER,
        available=True,
        detail="Optional dependency is installed.",
    )
