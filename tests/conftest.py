from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_root() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def copy_fixture_tree(tmp_path: Path, fixtures_root: Path) -> Callable[[str], Path]:
    def _copy(relative_path: str) -> Path:
        source = fixtures_root / relative_path
        destination = tmp_path / relative_path

        if not source.exists():
            raise FileNotFoundError(f"Fixture path does not exist: {source}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        return destination

    return _copy
