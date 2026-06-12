from __future__ import annotations

import importlib
from types import ModuleType

from pydantic import BaseModel, ConfigDict

from media_report.core.errors import OptionalDependencyMissingError

TRANSCRIPTION_PROVIDER = "faster-whisper"
TRANSCRIPTION_INSTALL_HINT = (
    '`pip install "media-report-cli[transcription]"` or `uv sync --extra transcription`.'
)


class TranscriptionCapability(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

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
