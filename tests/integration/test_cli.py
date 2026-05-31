import json
from dataclasses import replace
from pathlib import Path

from typer.testing import CliRunner

from media_report.cli.app import app
from media_report.core.errors import MediaProcessingExecutionError
from media_report.domain.artifacts.entities import PipelineStage, PipelineStageStatus
from media_report.domain.artifacts.service import ArtifactPlanner
from media_report.domain.media.entities import MediaProcessingResult, MediaSource
from media_report.infrastructure.ffmpeg.service import FFmpegService
from media_report.infrastructure.filesystem.metadata_repository import (
    JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner

runner = CliRunner()


def combined_output(result: object) -> str:
    stdout = getattr(result, "stdout", "")
    stderr = getattr(result, "stderr", "")
    return f"{stdout}{stderr}"


def structured_transcript_payload(text: str = "transcript") -> str:
    return json.dumps(
        {
            "provider": "stub",
            "model": "stub-small",
            "requested_language": None,
            "detected_language": "en",
            "segments": [
                {
                    "index": 0,
                    "start_seconds": 0.0,
                    "end_seconds": 1.0,
                    "text": text,
                }
            ],
        }
    )


def stub_media_processing(monkeypatch, *, fail_normalize: bool = False) -> None:
    def fake_extract(self, request):  # type: ignore[no-untyped-def]
        request.output_path.write_text("audio", encoding="utf-8")
        return MediaProcessingResult(
            output_path=request.output_path,
            command=("ffmpeg", "-i", str(request.source.path), str(request.output_path)),
            duration_ms=12,
            stderr_summary=None,
        )

    def fake_normalize(self, request):  # type: ignore[no-untyped-def]
        if fail_normalize:
            raise MediaProcessingExecutionError(
                operation="normalize_audio",
                exit_code=1,
                stderr_summary="normalization failed",
            )
        request.output_path.write_text("normalized", encoding="utf-8")
        return MediaProcessingResult(
            output_path=request.output_path,
            command=("ffmpeg", "-i", str(request.source_path), str(request.output_path)),
            duration_ms=15,
            stderr_summary=None,
        )

    monkeypatch.setattr(FFmpegService, "extract_audio", fake_extract)
    monkeypatch.setattr(FFmpegService, "normalize_audio", fake_normalize)


def write_resume_ready_metadata(media_path: Path) -> Path:
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(media_path)
    source = FileSystemMediaScanner().classify(media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=media_path, kind=source.kind),
        artifact_plan=artifact_plan,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language=None,
        selected_stages=tuple(PipelineStage),
    )
    completed_stage = replace(
        metadata.stages[PipelineStage.TRANSCRIBE],
        status=PipelineStageStatus.COMPLETED,
        finished_at=metadata.generated_at,
    )
    metadata = replace(
        metadata,
        stages={
            **metadata.stages,
            PipelineStage.EXTRACT_AUDIO: replace(
                metadata.stages[PipelineStage.EXTRACT_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
            PipelineStage.NORMALIZE_AUDIO: replace(
                metadata.stages[PipelineStage.NORMALIZE_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
            PipelineStage.TRANSCRIBE: completed_stage,
        },
    )
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")
    artifact_plan.audio_normalized.write_text("audio", encoding="utf-8")
    artifact_plan.transcript_raw.write_text("transcript", encoding="utf-8")
    artifact_plan.transcript_segments.write_text(
        structured_transcript_payload(),
        encoding="utf-8",
    )
    return artifact_plan.root_dir


def test_root_help_exposes_bootstrap_contract() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Process local media" in result.stdout
    assert "process" in result.stdout
    assert "doctor" in result.stdout
    assert "config" in result.stdout
    assert "templates" in result.stdout
    assert "Process or resume local media through audio preparation stages." in result.stdout
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
    assert "Process or resume local media through audio preparation stages." in result.stdout
    for flag in (
        "--recursive",
        "--resume",
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
    assert "Deprecated alias for --resume" in result.stdout
    assert "--only-report" in result.stdout


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


def test_process_creates_artifact_directory_and_metadata(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    stub_media_processing(monkeypatch)

    result = runner.invoke(app, ["process", str(single_media_path)])

    artifact_dir = single_media_path.parent / f"{single_media_path.stem}_media_report"
    metadata_path = artifact_dir / "metadata.json"
    log_path = artifact_dir / "pipeline.log"

    assert result.exit_code == 0
    assert artifact_dir.exists()
    assert metadata_path.exists()
    assert log_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["schema_version"] == 2
    assert metadata["workflow"]["language"] is None
    assert metadata["workflow"]["selected_stages"] == [
        "extract_audio",
        "normalize_audio",
        "transcribe",
        "report",
        "pdf",
    ]
    assert metadata["stages"]["extract_audio"]["status"] == "completed"
    assert metadata["stages"]["normalize_audio"]["status"] == "completed"
    assert metadata["stages"]["transcribe"]["status"] == "planned"
    assert metadata["stages"]["transcribe"]["started_at"] is None
    assert metadata["stages"]["transcribe"]["finished_at"] is None
    assert metadata["stages"]["transcribe"]["updated_at"] == metadata["generated_at"]
    assert metadata["stages"]["transcribe"]["error"] is None
    assert (artifact_dir / "audio_extracted.wav").exists()
    assert (artifact_dir / "audio_normalized.wav").exists()
    assert "metadata initialized (schema v2)" in log_path.read_text(encoding="utf-8")
    assert "extract_audio: planned" in result.stdout
    assert "report: planned" in result.stdout
    assert "pdf: planned" in result.stdout
    assert "extract_audio status: completed" in result.stdout
    assert "normalize_audio status: completed" in result.stdout


def test_process_only_transcribe_limits_planned_stages(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    stub_media_processing(monkeypatch)

    result = runner.invoke(app, ["process", str(single_media_path), "--only-transcribe"])
    metadata_path = (
        single_media_path.parent / f"{single_media_path.stem}_media_report" / "metadata.json"
    )

    assert result.exit_code == 0
    assert "extract_audio: planned" in result.stdout
    assert "normalize_audio: planned" in result.stdout
    assert "transcribe: planned" in result.stdout
    assert "report: skipped" in result.stdout
    assert "pdf: skipped" in result.stdout
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["workflow"]["selected_stages"] == [
        "extract_audio",
        "normalize_audio",
        "transcribe",
    ]
    assert metadata["stages"]["extract_audio"]["status"] == "completed"
    assert metadata["stages"]["normalize_audio"]["status"] == "completed"
    assert metadata["stages"]["transcribe"]["status"] == "planned"
    assert metadata["stages"]["report"]["status"] == "skipped"
    assert metadata["stages"]["report"]["finished_at"] == metadata["generated_at"]
    assert metadata["stages"]["pdf"]["status"] == "skipped"


def test_process_only_report_requires_existing_transcription(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    result = runner.invoke(app, ["process", str(single_media_path), "--only-report"])

    assert result.exit_code == 1
    assert "Cannot start a fresh pipeline at 'report'" in result.stdout
    assert "--resume" in result.stdout


def test_process_fails_when_artifacts_exist_without_resume(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    artifact_dir = single_media_path.parent / f"{single_media_path.stem}_media_report"
    artifact_dir.mkdir()

    result = runner.invoke(app, ["process", str(single_media_path)])

    assert result.exit_code == 2
    assert "--resume" in result.stdout


def test_process_recursive_directory_plans_supported_media_only(
    tmp_path: Path, monkeypatch, recursive_fixture_dir: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    stub_media_processing(monkeypatch)
    input_dir = recursive_fixture_dir
    expected_sources = FileSystemMediaScanner().scan(input_dir, recursive=True)

    result = runner.invoke(app, ["process", str(input_dir), "--recursive"])

    assert result.exit_code == 0
    assert f"Processed {len(expected_sources)} artifact directories." in result.stdout
    assert not (input_dir / "notes_media_report").exists()
    for source in expected_sources:
        artifact_dir = source.path.parent / f"{source.path.stem}_media_report"
        metadata = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))

        assert artifact_dir.exists()
        assert metadata["source"]["path"].endswith(source.path.name)
        assert metadata["source"]["kind"] == source.kind.value
        assert metadata["stages"]["extract_audio"]["status"] == "completed"
        assert metadata["stages"]["normalize_audio"]["status"] == "completed"


def test_process_invalid_path_exits_with_code_one(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    result = runner.invoke(app, ["process", str(tmp_path / "missing.mp4")])

    assert result.exit_code == 1
    assert "Input path does not exist" in result.stdout


def test_process_resume_reuses_completed_transcription_artifacts(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    stub_media_processing(monkeypatch)
    artifact_root = write_resume_ready_metadata(single_media_path)

    result = runner.invoke(app, ["process", str(single_media_path), "--resume", "--only-report"])

    assert result.exit_code == 0
    assert "extract_audio: reused" in result.stdout
    assert "normalize_audio: reused" in result.stdout
    assert "transcribe: reused" in result.stdout
    assert "report: planned" in result.stdout
    assert "pdf: planned" in result.stdout
    metadata = json.loads((artifact_root / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["workflow"]["selected_stages"] == ["report", "pdf"]
    assert "extract_audio status: completed" in result.stdout
    assert "normalize_audio status: completed" in result.stdout


def test_process_overwrite_warns_and_behaves_like_resume(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    stub_media_processing(monkeypatch)
    write_resume_ready_metadata(single_media_path)

    result = runner.invoke(app, ["process", str(single_media_path), "--overwrite", "--only-report"])

    assert result.exit_code == 0
    assert "--overwrite is deprecated" in result.stdout
    assert "report: planned" in result.stdout


def test_process_resume_fails_for_corrupt_metadata(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    artifact_dir = single_media_path.parent / f"{single_media_path.stem}_media_report"
    artifact_dir.mkdir()
    (artifact_dir / "metadata.json").write_text("{not-json", encoding="utf-8")

    result = runner.invoke(app, ["process", str(single_media_path), "--resume"])

    assert result.exit_code == 1
    assert "Invalid artifact metadata" in result.stdout


def test_process_resume_fails_when_metadata_is_missing_but_artifacts_exist(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    artifact_dir = single_media_path.parent / f"{single_media_path.stem}_media_report"
    artifact_dir.mkdir()
    (artifact_dir / "pipeline.log").write_text("orphaned artifact root\n", encoding="utf-8")
    (artifact_dir / "transcript_raw.txt").write_text("transcript", encoding="utf-8")
    (artifact_dir / "transcript_segments.json").write_text(
        structured_transcript_payload(),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["process", str(single_media_path), "--resume", "--only-report"])

    assert result.exit_code == 1
    assert "Artifact metadata is missing" in result.stdout
    assert "metadata.json" in result.stdout


def test_process_resume_fails_for_incomplete_completed_stage(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    artifact_root = write_resume_ready_metadata(single_media_path)
    (artifact_root / "transcript_segments.json").unlink()

    result = runner.invoke(app, ["process", str(single_media_path), "--resume", "--only-report"])

    assert result.exit_code == 1
    assert "required artifacts are" in result.stdout
    assert "missing: transcript_segments.json" in result.stdout


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


def test_process_persists_partial_failure_during_normalize(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    stub_media_processing(monkeypatch, fail_normalize=True)

    result = runner.invoke(app, ["process", str(single_media_path)])
    artifact_dir = single_media_path.parent / f"{single_media_path.stem}_media_report"
    metadata = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert metadata["stages"]["extract_audio"]["status"] == "completed"
    assert metadata["stages"]["normalize_audio"]["status"] == "failed"
    assert metadata["stages"]["normalize_audio"]["error"]["code"] == "execution_failed"
    assert (artifact_dir / "audio_extracted.wav").exists()
    assert not (artifact_dir / "audio_normalized.wav").exists()


def test_process_resume_executes_only_normalize_when_extract_is_completed(
    tmp_path: Path, monkeypatch, single_media_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    planner = ArtifactPlanner()
    artifact_plan = planner.prepare_new(single_media_path)
    source = FileSystemMediaScanner().classify(single_media_path)
    metadata = planner.bootstrap_metadata(
        source=MediaSource(path=single_media_path, kind=source.kind),
        artifact_plan=artifact_plan,
        template_name="generic",
        llm_provider="ollama",
        llm_model="llama3.1",
        output_format="pdf",
        language=None,
        selected_stages=tuple(PipelineStage),
    )
    metadata = replace(
        metadata,
        stages={
            **metadata.stages,
            PipelineStage.EXTRACT_AUDIO: replace(
                metadata.stages[PipelineStage.EXTRACT_AUDIO],
                status=PipelineStageStatus.COMPLETED,
                finished_at=metadata.generated_at,
            ),
        },
    )
    JsonPipelineMetadataRepository().write(metadata)
    planner.initialize_log(artifact_plan.root_dir, metadata_schema_version=metadata.schema_version)
    artifact_plan.audio_extracted.write_text("audio", encoding="utf-8")

    def fail_if_extract_called(self, request):  # type: ignore[no-untyped-def]
        raise AssertionError("extract_audio should not be called during partial resume")

    def fake_normalize(self, request):  # type: ignore[no-untyped-def]
        request.output_path.write_text("normalized", encoding="utf-8")
        return MediaProcessingResult(
            output_path=request.output_path,
            command=("ffmpeg", "-i", str(request.source_path), str(request.output_path)),
            duration_ms=15,
            stderr_summary=None,
        )

    monkeypatch.setattr(FFmpegService, "extract_audio", fail_if_extract_called)
    monkeypatch.setattr(FFmpegService, "normalize_audio", fake_normalize)

    result = runner.invoke(app, ["process", str(single_media_path), "--resume"])
    refreshed = json.loads((artifact_plan.metadata_json).read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert refreshed["stages"]["extract_audio"]["status"] == "completed"
    assert refreshed["stages"]["normalize_audio"]["status"] == "completed"
    assert (artifact_plan.audio_normalized).exists()
