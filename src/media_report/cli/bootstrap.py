from __future__ import annotations

from media_report.application.process_media.service import ProcessMediaService
from media_report.application.transcribe.service import TranscribeService
from media_report.core.settings import AppSettings
from media_report.infrastructure.ffmpeg.service import FFmpegService
from media_report.infrastructure.filesystem.metadata_repository import (
    JsonPipelineMetadataRepository,
)
from media_report.infrastructure.filesystem.scanner import FileSystemMediaScanner
from media_report.infrastructure.filesystem.transcription_repository import (
    JsonTranscriptionArtifactRepository,
)
from media_report.infrastructure.resources.templates import PackagePromptTemplateRepository
from media_report.infrastructure.transcription import FasterWhisperProvider


def build_transcribe_service(settings: AppSettings) -> TranscribeService:
    scanner = FileSystemMediaScanner()
    metadata_repository = JsonPipelineMetadataRepository()
    media_processor = FFmpegService()
    return TranscribeService(
        scanner=scanner,
        metadata_repository=metadata_repository,
        media_processor=media_processor,
        transcription_provider=FasterWhisperProvider(default_model=settings.whisper_model),
        transcription_artifact_repository=JsonTranscriptionArtifactRepository(),
    )


def build_process_service(settings: AppSettings) -> ProcessMediaService:
    scanner = FileSystemMediaScanner()
    metadata_repository = JsonPipelineMetadataRepository()
    media_processor = FFmpegService()
    transcribe_service = TranscribeService(
        scanner=scanner,
        metadata_repository=metadata_repository,
        media_processor=media_processor,
        transcription_provider=FasterWhisperProvider(default_model=settings.whisper_model),
        transcription_artifact_repository=JsonTranscriptionArtifactRepository(),
    )
    return ProcessMediaService(
        scanner=scanner,
        templates=PackagePromptTemplateRepository(),
        metadata_repository=metadata_repository,
        transcribe_service=transcribe_service,
    )
