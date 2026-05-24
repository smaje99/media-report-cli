from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

SUPPORTED_MEDIA_EXTENSIONS = {
    ".avi",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".wav",
    ".webm",
}

PREFERRED_SINGLE_MEDIA_FILENAMES = (
    "profile_spanish.webm",
    "meeting_audio.wav",
    "meeting_video.mp4",
)


def _single_match(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one fixture matching '{pattern}' in {directory}, "
            f"found {len(matches)}."
        )
    return matches[0]


@pytest.fixture
def fixtures_root() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def copy_fixture_tree(tmp_path: Path, fixtures_root: Path) -> Callable[[str], Path]:
    def _copy(relative_path: str) -> Path:
        source = fixtures_root / relative_path
        destination = tmp_path / relative_path

        if not source.exists():
            pytest.skip(reason=f"Optional fixture path is not available locally: {source}")  # ty:ignore[unknown-argument]

        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        return destination

    return _copy


@pytest.fixture
def single_fixture_dir(copy_fixture_tree: Callable[[str], Path]) -> Path:
    return copy_fixture_tree("media/single")


@pytest.fixture
def recursive_fixture_dir(copy_fixture_tree: Callable[[str], Path]) -> Path:
    return copy_fixture_tree("media/recursive")


@pytest.fixture
def single_media_path(single_fixture_dir: Path) -> Path:
    for filename in PREFERRED_SINGLE_MEDIA_FILENAMES:
        candidate = single_fixture_dir / filename
        if candidate.exists():
            return candidate

    matches = sorted(
        path
        for path in single_fixture_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA_EXTENSIONS
    )
    if not matches:
        pytest.skip(
            reason=f"No supported single-file media fixtures found in {single_fixture_dir}."  # ty:ignore[unknown-argument]
        )
    return matches[0]
