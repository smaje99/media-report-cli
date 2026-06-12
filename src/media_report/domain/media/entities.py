from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class MediaKind(StrEnum):
    AUDIO = "audio"
    VIDEO = "video"


class MediaSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    kind: MediaKind


class ExtractAudioRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: MediaSource
    output_path: Path


class NormalizeAudioRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_path: Path
    output_path: Path


class MediaProcessingResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    output_path: Path
    command: tuple[str, ...]
    duration_ms: Annotated[int, Field(ge=0)]
    stderr_summary: str | None
