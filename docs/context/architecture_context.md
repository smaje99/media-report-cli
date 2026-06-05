# Architecture Context

## Style

The project uses hexagonal architecture with moderate vertical slicing.

## Layers

- `media_report.cli`: command definition and console UX
- `media_report.application`: workflow orchestration and use-case services
- `media_report.domain`: entities, value objects, ports, and domain rules
- `media_report.infrastructure`: filesystem, subprocess, HTTP, and package-resource adapters

## Stable Ports

- `TranscriptionProvider`
- `LLMProvider`
- `PromptTemplateRepository`
- `DocumentRenderer`
- `MediaProcessingService`

## Adapter-Local Typing

- Provider-specific SDK typing helpers stay inside the corresponding infrastructure adapter.
- Example: private `Protocol` definitions that describe the minimal `faster-whisper` module,
  model instance, or raw segment shape belong in
  `media_report.infrastructure.transcription.faster_whisper_provider`.
- These helper types are not stable ports and must not move into `media_report.domain`,
  because they describe external SDK details rather than business contracts.

## Key Decisions

- Resource loading goes through `importlib.resources`.
- Config is user-scoped and file-backed with env overrides.
- Artifact metadata is designed for resumable workflows even before resume support is implemented.
