from pathlib import Path

from typer.testing import CliRunner

from media_report.cli.app import app

runner = CliRunner()


def combined_output(result: object) -> str:
    stdout = getattr(result, "stdout", "")
    stderr = getattr(result, "stderr", "")
    return f"{stdout}{stderr}"


def test_root_help_exposes_bootstrap_contract() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Process local media" in result.stdout
    assert "process" in result.stdout
    assert "doctor" in result.stdout
    assert "config" in result.stdout
    assert "templates" in result.stdout
    assert "Prepare bootstrap artifacts and a stage plan for local media." in result.stdout
    assert "Inspect the local bootstrap environment and packaged resources." in result.stdout


def test_root_without_arguments_shows_help() -> None:
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Usage: media-report" in combined_output(result)
    assert "process" in combined_output(result)
    assert "doctor" in combined_output(result)


def test_process_help_documents_bootstrap_flag_contract() -> None:
    result = runner.invoke(app, ["process", "--help"])

    assert result.exit_code == 0
    assert "Prepare bootstrap artifacts" in result.stdout
    for flag in (
        "--recursive",
        "--overwrite",
        "--provider",
        "--model",
        "--language",
        "--template",
        "--output-format",
        "--only-transcribe",
        "--only-report",
    ):
        assert flag in result.stdout
    assert "Active in 0.1.0" in result.stdout
    assert "Planning flag in 0.1.0" in result.stdout
    assert "Stable roadmap placeholder" in result.stdout


def test_config_help_exposes_public_commands_only() -> None:
    result = runner.invoke(app, ["config", "--help"])

    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "show" in result.stdout
    assert "example" not in result.stdout


def test_doctor_help_exits_zero() -> None:
    result = runner.invoke(app, ["doctor", "--help"])

    assert result.exit_code == 0
    assert "Inspect the local bootstrap environment and packaged resources." in result.stdout


def test_templates_help_exits_zero() -> None:
    result = runner.invoke(app, ["templates", "--help"])

    assert result.exit_code == 0
    assert "Inspect bundled templates." in result.stdout


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


def test_config_init_existing_file_exits_with_code_two(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text("[llm]\n", encoding="utf-8")

    result = runner.invoke(app, ["config", "init", "--path", str(target)])

    assert result.exit_code == 2
    assert "already exists" in result.stdout


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


def test_process_only_transcribe_limits_planned_stages(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    media_file = tmp_path / "meeting.mp4"
    media_file.write_text("fake media", encoding="utf-8")

    result = runner.invoke(app, ["process", str(media_file), "--only-transcribe"])

    assert result.exit_code == 0
    assert "EXTRACT_AUDIO" in result.stdout
    assert "NORMALIZE_AUDIO" in result.stdout
    assert "TRANSCRIBE" in result.stdout
    assert "REPORT" not in result.stdout
    assert " PDF " not in result.stdout


def test_process_only_report_limits_planned_stages(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    media_file = tmp_path / "meeting.mp4"
    media_file.write_text("fake media", encoding="utf-8")

    result = runner.invoke(app, ["process", str(media_file), "--only-report"])

    assert result.exit_code == 0
    assert "REPORT" in result.stdout
    assert "PDF" in result.stdout
    assert "EXTRACT_AUDIO" not in result.stdout
    assert "NORMALIZE_AUDIO" not in result.stdout
    assert "TRANSCRIBE" not in result.stdout


def test_process_fails_when_artifacts_exist_without_overwrite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    media_file = tmp_path / "meeting.mp4"
    media_file.write_text("fake media", encoding="utf-8")
    artifact_dir = tmp_path / "meeting_media_report"
    artifact_dir.mkdir()

    result = runner.invoke(app, ["process", str(media_file)])

    assert result.exit_code == 2
    assert "--overwrite" in result.stdout


def test_process_invalid_path_exits_with_code_one(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    result = runner.invoke(app, ["process", str(tmp_path / "missing.mp4")])

    assert result.exit_code == 1
    assert "Input path does not exist" in result.stdout


def test_process_directory_without_supported_media_exits_with_code_one(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    input_dir = tmp_path / "notes"
    input_dir.mkdir()
    (input_dir / "readme.txt").write_text("not media", encoding="utf-8")

    result = runner.invoke(app, ["process", str(input_dir)])

    assert result.exit_code == 1
    assert "No supported audio or video files were found." in result.stdout


def test_process_missing_path_argument_exits_with_code_two() -> None:
    result = runner.invoke(app, ["process"])

    assert result.exit_code == 2
    assert "Missing argument 'PATH'" in combined_output(result)
