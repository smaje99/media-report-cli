from pathlib import Path

from media_report.infrastructure.document.pandoc_service import PandocService
from media_report.infrastructure.ffmpeg.service import FFmpegService


def test_ffmpeg_command_construction() -> None:
  command = FFmpegService.build_extract_command(Path("in.mp4"), Path("out.wav"))

  assert command[:4] == ["ffmpeg", "-y", "-i", "in.mp4"]
  assert "-ac" in command
  assert "-ar" in command
  assert command[-1] == "out.wav"


def test_ffmpeg_normalize_command_construction() -> None:
  command = FFmpegService.build_normalize_command(Path("in.wav"), Path("normalized.wav"))

  assert command[:4] == ["ffmpeg", "-y", "-i", "in.wav"]
  assert "-af" in command
  assert "loudnorm" in command
  assert command[-1] == "normalized.wav"


def test_pandoc_command_construction() -> None:
  command = PandocService.build_command(
    Path("report.md"),
    Path("report.pdf"),
    Path("default.tex"),
  )

  assert command[0] == "pandoc"
  assert "--pdf-engine=xelatex" in command
  assert command[-1] == "report.pdf"
