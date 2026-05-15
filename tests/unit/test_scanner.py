from pathlib import Path

import pytest

from media_report.core.errors import InputPathError
from media_report.domain.media.entities import MediaKind
from media_report.infrastructure.filesystem.scanner import (
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    FileSystemMediaScanner,
)


def test_classify_audio_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.mp3"
    file_path.write_text("x", encoding="utf-8")

    source = FileSystemMediaScanner().classify(file_path)

    assert source.kind == MediaKind.AUDIO


def test_classify_video_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.mp4"
    file_path.write_text("x", encoding="utf-8")

    source = FileSystemMediaScanner().classify(file_path)

    assert source.kind == MediaKind.VIDEO


def test_classify_rejects_unknown_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(InputPathError):
        FileSystemMediaScanner().classify(file_path)


def test_scan_recursively_discovers_nested_media_and_skips_unsupported(copy_fixture_tree) -> None:
    fixture_dir = copy_fixture_tree("media/recursive")

    sources = FileSystemMediaScanner().scan(fixture_dir, recursive=True)

    supported_extensions = SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS
    expected_paths = sorted(
        candidate.relative_to(fixture_dir).as_posix()
        for candidate in fixture_dir.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in supported_extensions
    )

    assert [source.path.relative_to(fixture_dir).as_posix() for source in sources] == expected_paths
    assert "notes.txt" not in expected_paths
    assert all(source.kind in {MediaKind.AUDIO, MediaKind.VIDEO} for source in sources)
