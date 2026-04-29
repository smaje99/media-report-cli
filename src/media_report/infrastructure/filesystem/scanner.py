from __future__ import annotations

from pathlib import Path

from media_report.core.constants import SUPPORTED_AUDIO_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS
from media_report.core.errors import InputPathError
from media_report.domain.media.entities import MediaKind, MediaSource


class FileSystemMediaScanner:
    def classify(self, path: Path) -> MediaSource:
        suffix = path.suffix.lower()
        if suffix in SUPPORTED_AUDIO_EXTENSIONS:
            return MediaSource(path=path, kind=MediaKind.AUDIO)
        if suffix in SUPPORTED_VIDEO_EXTENSIONS:
            return MediaSource(path=path, kind=MediaKind.VIDEO)
        raise InputPathError(f"Unsupported media type for path: {path}")

    def scan(self, directory: Path, recursive: bool) -> list[MediaSource]:
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        items: list[MediaSource] = []
        for candidate in iterator:
            if candidate.is_file():
                try:
                    items.append(self.classify(candidate))
                except InputPathError:
                    continue
        return sorted(items, key=lambda item: str(item.path))
