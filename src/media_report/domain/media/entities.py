from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class MediaKind(StrEnum):
    AUDIO = "audio"
    VIDEO = "video"


@dataclass(frozen=True)
class MediaSource:
    path: Path
    kind: MediaKind


@dataclass(frozen=True)
class ExtractAudioRequest:
    source: MediaSource
    output_path: Path


@dataclass(frozen=True)
class NormalizeAudioRequest:
    source_path: Path
    output_path: Path


@dataclass(frozen=True)
class MediaProcessingResult:
    output_path: Path
    command: tuple[str, ...]
    duration_ms: int
    stderr_summary: str | None
