from pathlib import Path

from typer.testing import CliRunner

from media_report.cli.app import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Process local media" in result.stdout


def test_templates_list() -> None:
    result = runner.invoke(app, ["templates", "list"])

    assert result.exit_code == 0
    assert "generic" in result.stdout
    assert "default.tex" in result.stdout


def test_config_init_writes_skeleton(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"

    result = runner.invoke(app, ["config", "init", "--path", str(target)])

    assert result.exit_code == 0
    assert target.exists()
    assert "[llm]" in target.read_text(encoding="utf-8")


def test_doctor_reports_dependencies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "prompt templates" in result.stdout
    assert "ffmpeg" in result.stdout


def test_process_creates_artifact_directory_and_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    media_file = tmp_path / "meeting.mp4"
    media_file.write_text("fake media", encoding="utf-8")

    result = runner.invoke(app, ["process", str(media_file)])

    artifact_dir = tmp_path / "meeting_media_report"
    metadata_path = artifact_dir / "metadata.json"
    log_path = artifact_dir / "pipeline.log"

    assert result.exit_code == 0
    assert artifact_dir.exists()
    assert metadata_path.exists()
    assert log_path.exists()


def test_process_fails_when_artifacts_exist_without_overwrite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    media_file = tmp_path / "meeting.mp4"
    media_file.write_text("fake media", encoding="utf-8")
    artifact_dir = tmp_path / "meeting_media_report"
    artifact_dir.mkdir()

    result = runner.invoke(app, ["process", str(media_file)])

    assert result.exit_code != 0
    assert "--overwrite" in result.stdout or result.exception is not None
