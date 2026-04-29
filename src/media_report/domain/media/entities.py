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
