from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class PipelineStage(StrEnum):
    EXTRACT_AUDIO = "extract_audio"
    NORMALIZE_AUDIO = "normalize_audio"
    TRANSCRIBE = "transcribe"
    REPORT = "report"
    PDF = "pdf"


@dataclass(frozen=True)
class ArtifactPlan:
    root_dir: Path
    metadata_json: Path
    pipeline_log: Path
    audio_extracted: Path
    audio_normalized: Path
    transcript_raw: Path
    transcript_segments: Path
    transcript_clean: Path
    prompt_used: Path
    llm_response_raw: Path
    report_markdown: Path
    report_pdf: Path


@dataclass(frozen=True)
class PipelineMetadata:
    payload: dict[str, Any]
